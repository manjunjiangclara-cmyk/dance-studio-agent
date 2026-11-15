"""Run only on disposable resources created by this invocation; always attempt cleanup."""

import argparse
import json
import math
import os
import shutil
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from .infrastructure import template

BACKEND = Path(__file__).resolve().parents[2]


def package(directory):
    target = directory / "lambda-package"
    target.mkdir()
    requirements = directory / "requirements.txt"
    with requirements.open("w") as stream:
        subprocess.run(
            ["uv", "export", "--frozen", "--no-dev", "--no-emit-project", "--no-editable"],
            cwd=BACKEND,
            stdout=stream,
            check=True,
        )
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python-version",
            "3.12",
            "--python-platform",
            "x86_64-manylinux_2_34",
            "--only-binary",
            ":all:",
            "--target",
            str(target),
            "--constraint",
            str(requirements),
            "langgraph",
            "psycopg[binary]",
            "sqlalchemy",
            "openai",
            "langsmith",
            "certifi",
        ],
        cwd=BACKEND,
        check=True,
    )
    for source in (BACKEND / "experiments", BACKEND / "src" / "studio_copilot"):
        shutil.copytree(
            source, target / source.name, ignore=shutil.ignore_patterns("__pycache__", "results")
        )
    output = directory / "lambda.zip"
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path in sorted(target.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(target))
    if sum(p.stat().st_size for p in target.rglob("*") if p.is_file()) > 250 * 1024 * 1024:
        raise ValueError("Lambda package exceeds the uncompressed size limit.")
    return output


def wait_stack(cf, stack, *, deleting=False, timeout=1800):
    from botocore.exceptions import ClientError

    deadline, last_print = time.monotonic() + timeout, 0
    while time.monotonic() < deadline:
        try:
            status = cf.describe_stacks(StackName=stack)["Stacks"][0]["StackStatus"]
        except ClientError as error:
            if (
                deleting
                and error.response["Error"]["Code"] == "ValidationError"
                and ("does not exist" in error.response["Error"].get("Message", ""))
            ):
                return
            raise
        if status == ("DELETE_COMPLETE" if deleting else "CREATE_COMPLETE"):
            return
        if not deleting and status.startswith("DELETE_"):
            raise RuntimeError("Validation stack creation failed and automatic deletion started.")
        if "FAILED" in status or status.endswith("ROLLBACK_COMPLETE"):
            raise RuntimeError(f"Validation stack ended in {status}.")
        if time.monotonic() - last_print >= 45:
            print(f"CloudFormation: {status}", flush=True)
            last_print = time.monotonic()
        time.sleep(10)
    raise TimeoutError("Validation stack operation exceeded its time window.")


def invoke(client, function, payload):
    response = client.invoke(FunctionName=function, Payload=json.dumps(payload).encode())
    result = json.load(response["Payload"])
    if response.get("FunctionError"):
        raise RuntimeError("Validation Lambda failed: " + result.get("errorType", "unknown"))
    return result


def equivalent(left, right):
    if isinstance(left, float) or isinstance(right, float):
        return (
            isinstance(left, (int, float))
            and isinstance(right, (int, float))
            and math.isclose(left, right, abs_tol=1e-6, rel_tol=0)
        )
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(equivalent(v, right[k]) for k, v in left.items())
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            equivalent(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def pause_check(cloudwatch, instance, *, timeout=900):
    since = datetime.now(UTC)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        metrics = cloudwatch.get_metric_statistics(
            Namespace="AWS/RDS",
            MetricName="ServerlessDatabaseCapacity",
            Dimensions=[{"Name": "DBInstanceIdentifier", "Value": instance}],
            StartTime=since,
            EndTime=datetime.now(UTC),
            Period=60,
            Statistics=["Minimum"],
        )["Datapoints"]
        if any(
            point["Minimum"] == 0 and point["Timestamp"] >= since + timedelta(seconds=300)
            for point in metrics
        ):
            return {
                "status": "passed",
                "elapsed_seconds": (datetime.now(UTC) - since).total_seconds(),
            }
        print("Waiting for Aurora capacity to reach zero (metrics only; no SQL probe).", flush=True)
        time.sleep(30)
    return {"status": "failed", "reason": "No zero-capacity datapoint within 15 minutes."}


def resume_check(sql, *, timeout=120):
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        try:
            assert sql.query("SELECT 1 AS ready") == [{"ready": 1}]
            return {"status": "passed", "seconds": time.monotonic() - started}
        except Exception as error:
            code = getattr(error, "response", {}).get("Error", {}).get("Code")
            if code not in {"DatabaseResumingException", "DatabaseUnavailableException"}:
                raise
            time.sleep(2)
    return {"status": "failed", "reason": "Database did not resume within two minutes."}


def cleanup(cf, s3, stack, outputs, artifact):
    result = {"artifact": {"status": "not_needed"}}
    if artifact:
        try:
            s3.delete_object(Bucket=outputs["Artifacts"], Key=artifact)
            result["artifact"] = {"status": "passed"}
        except Exception as error:
            result["artifact"] = {"status": "failed", "error_type": type(error).__name__}
    # A bucket failure must not prevent deletion of the independently billed database.
    try:
        try:
            state = cf.describe_stacks(StackName=stack)["Stacks"][0]["StackStatus"]
        except Exception as error:
            details = getattr(error, "response", {}).get("Error", {})
            state = (
                "DELETE_COMPLETE"
                if (
                    details.get("Code") == "ValidationError"
                    and "does not exist" in details.get("Message", "")
                )
                else None
            )
        if state not in {"DELETE_COMPLETE", "DELETE_IN_PROGRESS"}:
            cf.delete_stack(StackName=stack)
        if state != "DELETE_COMPLETE":
            wait_stack(cf, stack, deleting=True)
        result["stack"] = {"status": "passed"}
    except Exception as error:
        result["stack"] = {"status": "failed", "error_type": type(error).__name__}
    result["status"] = (
        "passed"
        if all(item["status"] in {"passed", "not_needed"} for item in result.values())
        else "failed"
    )
    return result


def live(directory, region, engine_version, zip_path=None):
    import boto3
    from botocore.config import Config

    from .sql import DataSQL

    session = boto3.Session(region_name=region)
    cf, s3 = session.client("cloudformation"), session.client("s3")
    lambdas = session.client("lambda", config=Config(read_timeout=320, retries={"max_attempts": 0}))
    name = "data-api-validation-" + uuid4().hex[:12]
    stack, outputs, artifact = None, {}, None
    report = {
        "status": "not_run",
        "region": region,
        "stack_name": name,
        "live_aws": True,
        "openai_calls": 0,
        "migration_ready": False,
        "checks": {k: {"status": "not_run"} for k in ("checkpoint", "mutex", "retrieval")},
    }
    report_file = directory / "report.json"

    def save():
        report_file.write_text(json.dumps(report, indent=2, default=str) + "\n")

    try:
        print("Creating a disposable validation stack.", flush=True)
        stack = cf.create_stack(
            StackName=name,
            TemplateBody=json.dumps(template(engine_version)),
            Capabilities=["CAPABILITY_IAM"],
            Tags=[{"Key": "Purpose", "Value": "data-api-validation"}],
            TimeoutInMinutes=30,
            OnFailure="DELETE",
        )["StackId"]
        report["stack_id"] = stack
        save()
        wait_stack(cf, stack)
        outputs = {
            o["OutputKey"]: o["OutputValue"]
            for o in cf.describe_stacks(StackName=stack)["Stacks"][0]["Outputs"]
        }
        archive = zip_path or package(directory)
        artifact = "validation.zip"
        s3.upload_file(str(archive), outputs["Artifacts"], artifact)
        for name in ("Api", "Baseline"):
            lambdas.update_function_code(
                FunctionName=outputs[name], S3Bucket=outputs["Artifacts"], S3Key=artifact
            )
            lambdas.get_waiter("function_updated_v2").wait(FunctionName=outputs[name])
            lambdas.update_function_configuration(
                FunctionName=outputs[name], Handler="experiments.data_api.lambda_function.handler"
            )
            lambdas.get_waiter("function_updated_v2").wait(FunctionName=outputs[name])
        schema = "data_api_" + uuid4().hex
        started = time.monotonic()
        result = invoke(lambdas, outputs["Api"], {"action": "validate", "schema": schema})
        report.update(result)
        report["cold_validation_seconds"] = time.monotonic() - started
        if result["checks"]["retrieval"]["status"] == "passed":
            baseline = invoke(
                lambdas, outputs["Baseline"], {"action": "direct_baseline", "schema": schema}
            )
            parity = equivalent(result["checks"]["retrieval"]["result"], baseline["result"])
            report["direct_driver_parity"] = {
                "status": "passed" if parity else "failed",
                "score_tolerance": 1e-6,
            }
            if not parity:
                report["status"] = "failed"
        sql = DataSQL(
            session.client("rds-data", config=Config(retries={"total_max_attempts": 1})),
            outputs["ClusterArn"],
            outputs["SecretArn"],
        )
        sql.query(f"DROP SCHEMA {schema} CASCADE")
        try:
            report["auto_pause"] = pause_check(session.client("cloudwatch"), outputs["WriterId"])
            if report["auto_pause"]["status"] == "passed":
                report["cold_resume"] = resume_check(sql)
        except Exception as error:
            report["auto_pause"] = {"status": "not_run", "error_type": type(error).__name__}
        if report["auto_pause"]["status"] != "passed" and report["status"] == "passed":
            report["status"] = "incomplete"
        if report.get("cold_resume", {}).get("status") == "failed":
            report["status"] = "failed"
    except Exception as error:
        report["error_type"] = type(error).__name__
        if hasattr(error, "response"):
            report["aws_error_code"] = error.response.get("Error", {}).get("Code")
            report["aws_operation"] = getattr(error, "operation_name", None)
        report["status"] = "failed" if stack else "not_run"
        if stack:
            try:
                events = cf.describe_stack_events(StackName=stack)["StackEvents"]
                report["provisioning_failures"] = [
                    {
                        k: event.get(k)
                        for k in ("LogicalResourceId", "ResourceStatus", "ResourceStatusReason")
                    }
                    for event in events
                    if event["ResourceStatus"].endswith("FAILED")
                ]
            except Exception as diagnostic_error:
                report["provisioning_diagnostics"] = {
                    "status": "not_run",
                    "error_type": type(diagnostic_error).__name__,
                    "required_action": "cloudformation:DescribeStackEvents",
                }
    finally:
        if stack:
            report["cleanup"] = cleanup(cf, s3, stack, outputs, artifact)
            if report["cleanup"]["status"] != "passed":
                report["status"] = "incomplete"
        else:
            report["cleanup"] = {
                "status": "not_needed",
                "reason": "Stack creation was not accepted.",
            }
        save()
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": str(report_file),
                "aws_error_code": report.get("aws_error_code"),
                "cleanup": report["cleanup"],
            }
        ),
        flush=True,
    )
    return 0 if report["status"] == "passed" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["template", "package", "live"])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--region", default="ap-southeast-2")
    parser.add_argument("--lambda-zip", type=Path)
    args = parser.parse_args()
    if args.action == "template":
        print((BACKEND.parent / "infrastructure" / "express-validation" / "main.tf").read_text())
        return 0
    if args.output_dir is None:
        parser.error("--output-dir is required; use a new private results directory.")
    args.output_dir = args.output_dir.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    os.chmod(args.output_dir, 0o700)
    if args.action == "package":
        print(package(args.output_dir))
        return 0
    from .terraform_runner import live as terraform_live

    return terraform_live(args.output_dir, args.region, None, args.lambda_zip)


if __name__ == "__main__":
    raise SystemExit(main())
