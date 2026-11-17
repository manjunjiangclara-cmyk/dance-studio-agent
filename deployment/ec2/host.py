#!/usr/bin/python3
"""Root-only host helpers. Never emit secret payloads or credentials."""

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tarfile
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path("/srv/studio")
REQUIRED = (
    "POSTGRES_PASSWORD",
    "ADMIN_API_TOKEN",
    "SESSION_SECRET",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OWNER_EMAIL",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
)
OPTIONAL = ("OPENAI_BASE_URL", "OPENAI_EMBEDDING_MODEL", "OPENAI_EMBEDDING_BASE_URL")


def atomic_write(path, data, mode=0o600):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def env_text(values):
    result = []
    for key, value in values.items():
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key) or not isinstance(value, str):
            raise ValueError("Invalid environment configuration")
        # Compose single-quoted dotenv values are literal, including dollar signs.
        if any(c in value for c in "\n\r\x00'\\"):
            raise ValueError(f"Unsupported control/quote characters in {key}")
        result.append(f"{key}='{value}'\n")
    return "".join(result)


def validate_secret(payload):
    if not isinstance(payload, dict) or any(not payload.get(key) for key in REQUIRED):
        raise ValueError("Application secret is missing required settings")
    if len(payload["SESSION_SECRET"]) < 32 or len(payload["ADMIN_API_TOKEN"]) < 32:
        raise ValueError("Session/admin secrets must contain at least 32 characters")
    if not re.fullmatch(r"[A-Za-z0-9]{32,128}", payload["POSTGRES_PASSWORD"]):
        raise ValueError(
            "Use a persistent alphanumeric database password of at least 32 characters"
        )
    values = {key: payload[key] for key in (*REQUIRED, *OPTIONAL) if key in payload}
    env_text(values)
    return values


def configure(config, client):
    payload = json.loads(client.get_secret_value(SecretId=config["secret_arn"])["SecretString"])
    values = validate_secret(payload)
    password_file = ROOT / "config/database-password.sha256"
    password_hash = hashlib.sha256(values["POSTGRES_PASSWORD"].encode()).hexdigest()
    if password_file.exists() and password_file.read_text().strip() != password_hash:
        raise ValueError("Database password changes require an explicit database rotation")
    origin = payload.get("PUBLIC_BASE_URL", "https://" + config["domain"])
    parsed = urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.netloc != parsed.hostname
        or parsed.path
        or parsed.query
        or parsed.fragment
        or not re.fullmatch(r"[a-z0-9][a-z0-9.-]+[a-z0-9]", parsed.hostname)
    ):
        raise ValueError(
            "Use the configured public HTTPS hostname without credentials, port or path"
        )
    values.update(
        PUBLIC_BASE_URL=origin,
        STUDIO_PUBLIC_LIVE_DEMO="true",
        STUDIO_DOCUMENT_ANSWERS="true",
        STUDIO_TOKENIZER_CACHE="/app/assets/tokenizer",
        STUDIO_RERANKER_CACHE="/app/assets/reranker",
        STUDIO_POLICY_PATH="/data/policy/studio.yaml",
        STUDIO_PUBLIC_DEMO_DB="/data/public-demo/ledger.sqlite3",
    )
    atomic_write(ROOT / "config/app.env", env_text(values))
    atomic_write(ROOT / "config/domain", parsed.hostname + "\n")
    atomic_write(password_file, password_hash + "\n")


def extract_release(archive, target, expected):
    with open(archive, "rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected:
        raise ValueError("Release archive checksum mismatch")
    target = Path(target)
    with tarfile.open(archive, "r:gz") as source:
        for member in source.getmembers():
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or not (member.isfile() or member.isdir()):
                raise ValueError("Unsafe release archive member")
        source.extractall(target, filter="data")


def snapshot_files(destination):
    destination = Path(destination)
    shutil.copytree(ROOT / "policy", destination / "policy")
    ledger = ROOT / "public-demo/ledger.sqlite3"
    (destination / "public-demo").mkdir()
    if ledger.exists():
        # Application is stopped by backup.sh; SQLite's backup API also handles journals.
        with (
            sqlite3.connect(ledger) as source,
            sqlite3.connect(destination / "public-demo/ledger.sqlite3") as target,
        ):
            source.backup(target)
            target.execute("PRAGMA journal_mode=DELETE")
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Public demo ledger failed integrity check")
    manifest = {}
    for path in destination.rglob("*"):
        if path.is_file():
            with path.open("rb") as stream:
                manifest[str(path.relative_to(destination))] = hashlib.file_digest(
                    stream, "sha256"
                ).hexdigest()
    atomic_write(destination / "checksums.json", json.dumps(manifest, sort_keys=True) + "\n")


def current_release():
    current = ROOT / "current"
    if not current.is_symlink() or not current.is_dir():
        return ""
    resolved = current.resolve()
    if resolved.parent != ROOT / "releases" or not re.fullmatch(r"[0-9a-f]{40}", resolved.name):
        raise ValueError("Current release is outside the deployment")
    return str(resolved)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=["configure", "download", "snapshot", "upload", "current"]
    )
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()
    if args.command == "current":
        print(current_release())
        return
    config = json.loads(Path("/etc/studio-host.json").read_text())
    import boto3

    session = boto3.Session(region_name=config["region"])
    if args.command == "configure":
        configure(config, session.client("secretsmanager"))
    elif args.command == "snapshot":
        snapshot_files(args.args[0])
    elif args.command == "upload":
        session.client("s3").upload_file(
            args.args[0],
            config["bucket"],
            args.args[1],
            ExtraArgs={"ServerSideEncryption": "AES256"},
        )
    else:
        sha, expected = args.args
        if not re.fullmatch(r"[0-9a-f]{40}", sha) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Invalid release identity")
        target = ROOT / "releases" / sha
        if target.exists():
            if (target / ".archive-sha256").read_text().strip() != expected:
                raise ValueError("Existing release identity differs")
            return
        with tempfile.TemporaryDirectory(dir=ROOT / "releases") as temporary:
            archive = Path(temporary) / "release.tar.gz"
            session.client("s3").download_file(
                config["bucket"], f"releases/{sha}.tar.gz", str(archive)
            )
            extracted = Path(temporary) / "source"
            extracted.mkdir()
            extract_release(archive, extracted, expected)
            atomic_write(extracted / ".archive-sha256", expected + "\n")
            extracted.rename(target)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # SDK errors can echo request arguments. Only report the exception type.
        raise SystemExit(f"Host operation failed ({type(error).__name__}); inspect configuration.")
