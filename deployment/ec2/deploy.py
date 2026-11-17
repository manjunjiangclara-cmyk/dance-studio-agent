#!/usr/bin/env python3
"""Explicit EC2 configuration and release commands; secret values never go to SSM."""

import argparse
import hashlib
import json
import re
import secrets
import shlex
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import boto3
from botocore.exceptions import ClientError
from host import OPTIONAL, REQUIRED, validate_secret

ROOT = Path(__file__).resolve().parents[2]
REGION = "ap-southeast-2"
ALLOWED_CONFIG = (
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_BASE_URL",
    "OPENAI_EMBEDDING_MODEL",
    "OPENAI_EMBEDDING_BASE_URL",
    "OWNER_EMAIL",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
)


def private_env(path):
    values = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, raw = line.removeprefix("export ").partition("=")
        key = key.strip()
        if key not in ALLOWED_CONFIG or not separator:
            continue
        parts = shlex.split(raw, comments=True)
        if len(parts) != 1:
            raise ValueError(f"Provide one quoted value for {key}")
        values[key] = parts[0]
    return values


def session():
    source = boto3.Session(region_name=REGION)
    account = source.client("sts").get_caller_identity()["Account"]
    credentials = source.client("sts").assume_role(
        RoleArn=f"arn:aws:iam::{account}:role/dance-studio-deployer",
        RoleSessionName="ec2-application-deployment",
    )["Credentials"]
    return boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name=REGION,
    )


def outputs():
    result = subprocess.run(
        [
            "terraform",
            f"-chdir={ROOT / 'infrastructure/ec2-demo'}",
            "output",
            "-json",
            "deployment",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def validate_target(clients, config):
    instance = clients.client("ec2").describe_instances(InstanceIds=[config["instance_id"]])[
        "Reservations"
    ][0]["Instances"][0]
    tags = {item["Key"]: item["Value"] for item in instance.get("Tags", [])}
    if tags.get("Project") != "dance-studio-agent" or tags.get("Purpose") != "ec2-application":
        raise ValueError("Refusing to operate on a server outside this deployment")


def configure(clients, config, env_file):
    client = clients.client("secretsmanager")
    try:
        existing = json.loads(
            client.get_secret_value(SecretId=config["secret_arn"])["SecretString"]
        )
    except ClientError as error:
        if error.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
        existing = {}
    values = {key: existing[key] for key in (*REQUIRED, *OPTIONAL) if key in existing}
    values.update(private_env(env_file))
    values["PUBLIC_BASE_URL"] = config["origin"]
    for key in ("POSTGRES_PASSWORD", "ADMIN_API_TOKEN", "SESSION_SECRET"):
        values.setdefault(key, secrets.token_hex(32))
    validate_secret(values)
    client.put_secret_value(SecretId=config["secret_arn"], SecretString=json.dumps(values))
    print("Application configuration stored; secret values were not printed.")
    print("Register the exact Google redirect URI:", config["callback"])


def release(clients, config):
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        raise ValueError("Commit the reviewed release first; deployment requires a clean checkout")
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "release.tar.gz"
        with archive.open("wb") as stream:
            subprocess.run(
                ["git", "archive", "--format=tar.gz", sha],
                cwd=ROOT,
                stdout=stream,
                check=True,
            )
        with archive.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        clients.client("s3").upload_file(
            str(archive),
            config["bucket"],
            f"releases/{sha}.tar.gz",
            ExtraArgs={"ServerSideEncryption": "AES256"},
        )
    # Only immutable non-secret identities enter SSM's command history.
    command = clients.client("ssm").send_command(
        InstanceIds=[config["instance_id"]],
        DocumentName="AWS-RunShellScript",
        Parameters={
            "commands": [f"/usr/local/bin/studio-release {sha} {checksum}"],
            "executionTimeout": ["3600"],
        },
        TimeoutSeconds=600,
        Comment="Deploy reviewed Dance Studio application release",
    )["Command"]["CommandId"]
    print("Deployment command:", command, flush=True)
    ssm = clients.client("ssm")
    for attempt in range(370):
        try:
            result = ssm.get_command_invocation(CommandId=command, InstanceId=config["instance_id"])
        except ssm.exceptions.InvocationDoesNotExist:
            time.sleep(10)
            continue
        status = result["Status"]
        if status not in {"Pending", "InProgress", "Delayed", "Cancelling"}:
            print("Release status:", status)
            if status != "Success":
                # Do not echo arbitrary provider/container output containing environment errors.
                raise RuntimeError("Deployment failed; inspect the private SSM invocation output")
            return
        if attempt % 6 == 0:
            print("Release:", status, flush=True)
        time.sleep(10)
    raise RuntimeError("Deployment observation timed out; inspect command status before retrying")


def smoke(origin):
    if not origin.startswith("https://"):
        raise ValueError("Verify the public HTTPS origin")
    # Caddy may still be acquiring its first certificate when containers become healthy.
    # Keep certificate verification enabled throughout the bounded readiness wait.
    for attempt in range(36):
        try:
            with urlopen(origin + "/health", timeout=10) as response:
                if response.status == 200:
                    break
        except (URLError, HTTPError):
            if attempt == 35:
                raise
        time.sleep(5)
    for path in ("/health", "/demo", "/workspace", "/auth/me"):
        with urlopen(origin + path, timeout=30) as response:
            body = response.read()
            assert response.status == 200
            if path == "/auth/me":
                assert json.loads(body) == {
                    "authenticated": False,
                    "login_available": True,
                }
            elif path == "/demo":
                assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', body.decode())
                assert assets
                for asset in assets:
                    with urlopen(origin + asset, timeout=30) as resource:
                        assert resource.status == 200
    for path in ("/api/v1/students", "/api/v1/documents"):
        try:
            urlopen(origin + path, timeout=30)
        except HTTPError as error:
            assert error.code == 401
        else:
            raise AssertionError("Private API unexpectedly allowed anonymous access")
    request = Request(
        origin + "/api/public-demo/runs",
        data=json.dumps(
            {"scenario": "booking", "request_id": "e228b891-839a-47b6-87dc-d3b65b374019"}
        ).encode(),
        headers={"Origin": "https://wrong.example", "Content-Type": "application/json"},
    )
    try:
        urlopen(request, timeout=30)
    except HTTPError as error:
        assert error.code == 403
    print("HTTPS, assets, owner configuration and anonymous access checks passed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    config = commands.add_parser("configure")
    config.add_argument("--env-file", type=Path, required=True)
    commands.add_parser("release")
    commands.add_parser("smoke")
    args = parser.parse_args()
    deployment = outputs()
    if args.command == "smoke":
        smoke(deployment["origin"])
        return
    clients = session()
    validate_target(clients, deployment)
    if args.command == "configure":
        configure(clients, deployment, args.env_file)
    else:
        release(clients, deployment)
        smoke(deployment["origin"])


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(
            f"Deployment stopped ({type(error).__name__}). No secret payloads printed."
        )
