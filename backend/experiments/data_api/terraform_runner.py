"""Native Terraform lifecycle with private state and unconditional destroy attempts."""

import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from uuid import uuid4


def live(directory, region, engine_version, zip_path=None):
    import boto3
    from botocore.config import Config

    from .__main__ import equivalent, invoke, package, pause_check, resume_check
    from .sql import DataSQL

    if region != "ap-southeast-2":
        raise ValueError("The approved deployment role is restricted to Sydney.")
    source = Path(__file__).resolve().parents[3] / "infrastructure" / "express-validation"
    working = directory / "terraform"
    working.mkdir(mode=0o700)
    for name in ("main.tf", ".terraform.lock.hcl"):
        shutil.copyfile(source / name, working / name)
    report = {
        "status": "not_run",
        "migration_ready": False,
        "openai_calls": 0,
        "provisioner": "terraform",
        "checks": {key: {"status": "not_run"} for key in ("checkpoint", "mutex", "retrieval")},
    }
    variables = {}
    attempted = False
    auth_attempted = False
    phase = "provision"

    def terraform(*arguments):
        with (directory / "terraform.log").open("a") as log:
            process = subprocess.Popen(
                ["terraform", f"-chdir={working}", *arguments],
                stdout=log,
                stderr=subprocess.STDOUT,
                env=environment,
            )
            try:
                while process.poll() is None:
                    print(
                        f"Terraform {arguments[0]} running; details in private terraform.log",
                        flush=True,
                    )
                    try:
                        process.wait(timeout=45)
                    except subprocess.TimeoutExpired:
                        pass
            except BaseException:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                raise
            if process.returncode:
                raise RuntimeError(f"Terraform {arguments[0]} failed; inspect the private log.")

    environment = dict(os.environ)
    try:
        account = boto3.client("sts").get_caller_identity()["Account"]
        role = f"arn:aws:iam::{account}:role/dance-studio-deployer"
        archive = zip_path or package(directory)
        variables = dict(
            name="data-api-validation-" + uuid4().hex[:12],
            deployer_role_arn=role,
            lambda_zip=str(archive.resolve()),
            python_executable=sys.executable,
            backend_directory=str(Path(__file__).resolve().parents[2]),
        )
        # Non-secret inputs allow cleanup to be resumed with the original private state.
        (working / "terraform.tfvars.json").write_text(json.dumps(variables, indent=2) + "\n")
        environment.update({"TF_VAR_" + k: v for k, v in variables.items()})
        plugins = source / ".terraform" / "providers"
        terraform("init", "-input=false", *([f"-plugin-dir={plugins}"] if plugins.exists() else []))
        terraform("plan", "-input=false", "-out=validation.tfplan")
        attempted = True
        terraform("apply", "-input=false", "validation.tfplan")
        outputs = json.loads(
            subprocess.check_output(
                ["terraform", f"-chdir={working}", "output", "-json", "connection"], env=environment
            )
        )
        credentials = boto3.client("sts").assume_role(
            RoleArn=role, RoleSessionName="data-api-validation"
        )["Credentials"]
        session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
            region_name=region,
        )
        client = session.client(
            "lambda", config=Config(read_timeout=320, retries={"total_max_attempts": 1})
        )
        schema = "data_api_" + uuid4().hex
        from .express import database, permissions

        phase = "iam_grant"
        auth_attempted = True
        permissions(outputs["ResourceId"], directory)
        phase = "database_initialization"
        database(session, outputs, schema)
        # Cloud Control rejects an Express update even when only HTTP enablement changes.
        # Use the documented RDS operation after password-user initialization instead.
        phase = "enable_data_api"
        enabled = session.client("rds").enable_http_endpoint(ResourceArn=outputs["ClusterArn"])
        report["endpoint_enablement"] = {
            "http_endpoint_enabled": enabled.get("HttpEndpointEnabled")
        }
        if not enabled.get("HttpEndpointEnabled"):
            raise RuntimeError("RDS did not confirm Data API enablement.")
        cluster = session.client("rds").describe_db_clusters(
            DBClusterIdentifier=outputs["ClusterId"]
        )["DBClusters"][0]
        outputs["WriterId"] = cluster["DBClusterMembers"][0]["DBInstanceIdentifier"]
        sql = DataSQL(
            session.client("rds-data", config=Config(retries={"total_max_attempts": 1})),
            outputs["ClusterArn"],
            outputs["SecretArn"],
        )
        phase = "data_api_readiness"
        report["data_api_readiness"] = resume_check(sql, timeout=300)
        assert report["data_api_readiness"]["status"] == "passed"
        assert sql.query("SELECT current_user AS identity") == [{"identity": "validator"}]
        phase = "mechanism_probes"
        result = invoke(
            client, outputs["Api"], {"action": "validate", "schema": schema, "schema_exists": True}
        )
        report.update(result)
        if result["checks"]["retrieval"]["status"] == "passed":
            phase = "direct_baseline"
            baseline = invoke(
                client, outputs["Baseline"], {"action": "direct_baseline", "schema": schema}
            )
            report["direct_driver_parity"] = equivalent(
                result["checks"]["retrieval"]["result"], baseline["result"]
            )
            if not report["direct_driver_parity"]:
                report["status"] = "failed"
        sql = DataSQL(
            session.client("rds-data", config=Config(retries={"total_max_attempts": 1})),
            outputs["ClusterArn"],
            outputs["SecretArn"],
        )
        print(
            json.dumps(
                {
                    "checks": {key: value["status"] for key, value in report["checks"].items()},
                    "direct_driver_parity": report.get("direct_driver_parity"),
                }
            ),
            flush=True,
        )
        if report["status"] != "passed":
            raise RuntimeError("Mechanism probes or direct-driver parity failed.")
        # Preserve mechanism evidence before the long metrics-only pause/cleanup waits.
        (directory / "report.json").write_text(
            json.dumps(
                {**report, "status": "in_progress", "phase": "auto_pause"}, indent=2, default=str
            )
            + "\n"
        )
        sql.query(f"DROP SCHEMA {schema} CASCADE")
        phase = "auto_pause"
        report["auto_pause"] = pause_check(session.client("cloudwatch"), outputs["WriterId"])
        if report["auto_pause"]["status"] == "passed":
            report["cold_resume"] = resume_check(sql)
        if report["status"] == "passed" and any(
            report.get(key, {}).get("status") != "passed" for key in ("auto_pause", "cold_resume")
        ):
            report["status"] = "incomplete"
    except BaseException as error:
        report["status"] = "failed" if attempted else "not_run"
        report["error_type"] = type(error).__name__
        report["failure_phase"] = getattr(error, "validation_phase", phase)
        report["sqlstate"] = getattr(error, "sqlstate", None)
        if hasattr(error, "validation_detail"):
            report["error_reason"] = error.validation_detail
        if hasattr(error, "response"):
            report["aws_error_code"] = error.response.get("Error", {}).get("Code")
        # PostgreSQL's privilege diagnostic contains no SQL statement or credentials.
        if report["sqlstate"] == "42501":
            report["error_reason"] = error.diag.message_primary
        (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    finally:
        if attempted:
            # A partial apply may not have recorded the Terraform destroy hook yet.
            try:
                from .delete_express import cleanup

                cleanup(role, variables["name"])
                report["no_snapshot_cleanup"] = {"status": "passed"}
            except BaseException as error:
                report["no_snapshot_cleanup"] = {
                    "status": "failed",
                    "error_type": type(error).__name__,
                }
            try:
                terraform("destroy", "-auto-approve", "-input=false")
                no_snapshot = report["no_snapshot_cleanup"]["status"] == "passed"
                report["cleanup"] = {"status": "passed" if no_snapshot else "failed"}
                if not no_snapshot:
                    report["status"] = "incomplete"
            except BaseException as error:
                report["cleanup"] = {"status": "failed", "error_type": type(error).__name__}
                report["status"] = "incomplete"
        else:
            report["cleanup"] = {"status": "not_needed"}
        if auth_attempted:
            try:
                from .express import permissions

                permissions("", directory)
                report["iam_grant_cleanup"] = {"status": "passed"}
            except BaseException as error:
                report["iam_grant_cleanup"] = {
                    "status": "failed",
                    "error_type": type(error).__name__,
                }
                report["cleanup"]["status"] = "failed"
                report["status"] = "incomplete"
        (directory / "report.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({"status": report["status"], "report": str(directory / "report.json")}))
    return 0 if report["status"] == "passed" else 1
