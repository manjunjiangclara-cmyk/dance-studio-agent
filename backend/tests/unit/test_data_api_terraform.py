import json

import boto3
import pytest

from experiments.data_api.terraform_runner import live


@pytest.mark.parametrize("interrupted", [False, True])
@pytest.mark.parametrize("no_snapshot_failure", [False, True])
def test_partial_terraform_apply_always_attempts_destroy(
    tmp_path, monkeypatch, interrupted, no_snapshot_failure
):
    from experiments.data_api import delete_express, terraform_runner

    cleanup_calls = []

    def cleanup(*args):
        cleanup_calls.append(args)
        if no_snapshot_failure:
            raise RuntimeError("synthetic direct cleanup failure")

    monkeypatch.setattr(delete_express, "cleanup", cleanup)

    class STS:
        def get_caller_identity(self):
            return {"Account": "123456789012"}

    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: STS())
    actions = []
    signals = []

    class Process:
        def __init__(self, command, **kwargs):
            actions.append(command[2])
            self.returncode = 1 if command[2] == "apply" else 0
            if interrupted and command[2] == "apply":
                self.returncode = None

        def poll(self):
            return self.returncode

        def wait(self, **kwargs):
            if not signals:
                raise KeyboardInterrupt()
            self.returncode = 1
            return self.returncode

        def send_signal(self, value):
            signals.append(value)

    monkeypatch.setattr(terraform_runner.subprocess, "Popen", Process)
    archive = tmp_path / "fixture.zip"
    archive.write_bytes(b"synthetic")
    assert live(tmp_path, "ap-southeast-2", "17.9", archive) == 1
    assert actions == ["init", "plan", "apply", "destroy"]
    report = json.loads((tmp_path / "report.json").read_text())
    assert len(cleanup_calls) == 1
    assert cleanup_calls[0][1].startswith("data-api-validation-")
    assert report["status"] == ("incomplete" if no_snapshot_failure else "failed")
    assert report["cleanup"]["status"] == ("failed" if no_snapshot_failure else "passed")
    assert report["migration_ready"] is False
    assert bool(signals) is interrupted


def test_terraform_runner_rejects_unapproved_region(tmp_path):
    with pytest.raises(ValueError, match="Sydney"):
        live(tmp_path, "us-east-1", "17.9")


@pytest.mark.parametrize("failure", ["grant", "database", "enable", "probe"])
@pytest.mark.parametrize("cleanup_failure", [None, "destroy", "interrupt", "revoke"])
def test_partial_auth_always_destroys_and_revokes(tmp_path, monkeypatch, failure, cleanup_failure):
    from experiments.data_api import delete_express, express, terraform_runner

    monkeypatch.setattr(delete_express, "cleanup", lambda *args: None)

    class STS:
        def get_caller_identity(self):
            return {"Account": "123456789012"}

        def assume_role(self, **kwargs):
            return {
                "Credentials": {
                    "AccessKeyId": "fixture",
                    "SecretAccessKey": "fixture",
                    "SessionToken": "fixture",
                }
            }

    class RDS:
        def describe_db_clusters(self, **kwargs):
            return {
                "DBClusters": [{"DBClusterMembers": [{"DBInstanceIdentifier": "fixture-writer"}]}]
            }

        def enable_http_endpoint(self, **kwargs):
            assert kwargs == {"ResourceArn": "fixture-cluster-arn"}
            if failure == "enable":
                raise RuntimeError("synthetic endpoint enablement failure")

    class Session:
        def client(self, name, **kwargs):
            return RDS() if name == "rds" else object()

    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: STS())
    monkeypatch.setattr(boto3, "Session", lambda **kwargs: Session())
    actions = []
    grants = []

    class Process:
        def __init__(self, command, **kwargs):
            action = command[2]
            actions.append(action)
            self.returncode = 0
            if action == "destroy":
                if cleanup_failure == "interrupt":
                    raise KeyboardInterrupt()
                self.returncode = int(cleanup_failure == "destroy")

        def poll(self):
            return self.returncode

    monkeypatch.setattr(terraform_runner.subprocess, "Popen", Process)
    monkeypatch.setattr(
        terraform_runner.subprocess,
        "check_output",
        lambda *args, **kwargs: (
            b'{"ResourceId":"cluster-fixture","ClusterArn":"fixture-cluster-arn","ClusterId":"fixture","SecretArn":"fixture","Api":"fixture"}'
        ),
    )

    def permissions(resource, directory):
        grants.append(resource)
        if (resource and failure == "grant") or (not resource and cleanup_failure == "revoke"):
            raise RuntimeError("synthetic IAM failure")

    def database(*args):
        if failure == "database":
            raise ValueError("synthetic DB failure")

    monkeypatch.setattr(express, "permissions", permissions)
    monkeypatch.setattr(express, "database", database)
    if failure == "probe":
        from experiments.data_api import __main__ as entrypoint
        from experiments.data_api import sql

        class DataSQL:
            def __init__(self, *args):
                pass

            def query(self, statement):
                return [{"ready": 1}] if "SELECT 1" in statement else [{"identity": "validator"}]

        monkeypatch.setattr(sql, "DataSQL", DataSQL)
        monkeypatch.setattr(
            entrypoint,
            "invoke",
            lambda *args: {
                "status": "failed",
                "checks": {
                    key: {"status": "failed", "reason": "synthetic"}
                    for key in ("checkpoint", "mutex", "retrieval")
                },
            },
        )
        monkeypatch.setattr(
            entrypoint,
            "pause_check",
            lambda *args: pytest.fail("Failed probes must skip the pause wait"),
        )
    archive = tmp_path / "fixture.zip"
    archive.write_bytes(b"synthetic")
    assert live(tmp_path, "ap-southeast-2", None, archive) == 1
    assert actions[-1] == "destroy"
    assert grants == ["cluster-fixture", ""]
    report = json.loads((tmp_path / "report.json").read_text())
    assert all(
        check["status"] == ("failed" if failure == "probe" else "not_run")
        for check in report["checks"].values()
    )
    assert report["status"] == ("incomplete" if cleanup_failure else "failed")
    assert report["iam_grant_cleanup"]["status"] == (
        "failed" if cleanup_failure == "revoke" else "passed"
    )
