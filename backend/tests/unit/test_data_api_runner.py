import json

import boto3
from botocore.exceptions import ClientError

from experiments.data_api.__main__ import cleanup, equivalent, live, wait_stack
from experiments.data_api.infrastructure import template


def test_disposable_template_has_no_nat_public_database_or_private_endpoint():
    resources = template()["Resources"]
    types = [r["Type"] for r in resources.values()]
    assert "AWS::EC2::NatGateway" not in types
    assert "AWS::EC2::VPCEndpoint" not in types
    assert resources["Writer"]["Properties"]["PubliclyAccessible"] is False
    assert resources["Cluster"]["Properties"]["ServerlessV2ScalingConfiguration"] == {
        "MinCapacity": 0,
        "MaxCapacity": 2,
        "SecondsUntilAutoPause": 300,
    }
    assert "VpcConfig" not in resources["Api"]["Properties"]
    assert resources["Cluster"]["DeletionPolicy"] == "Delete"
    assert "DB_PASSWORD" not in template()["Outputs"]


def test_permission_failure_is_not_a_feasibility_pass(tmp_path, monkeypatch):
    class CloudFormation:
        deleted = False

        def create_stack(self, **kwargs):
            raise ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "synthetic"}}, "CreateStack"
            )

        def delete_stack(self, **kwargs):
            self.deleted = True

    cf = CloudFormation()

    class Session:
        def client(self, service, **kwargs):
            return cf if service == "cloudformation" else object()

    monkeypatch.setattr(boto3, "Session", lambda **kwargs: Session())
    assert live(tmp_path, "ap-southeast-2", "17.9") == 1
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["status"] == "not_run" and report["migration_ready"] is False
    assert report["aws_operation"] == "CreateStack"
    assert all(check["status"] == "not_run" for check in report["checks"].values())
    assert not cf.deleted and report["cleanup"]["status"] == "not_needed"


def test_parity_requires_matching_structure_and_bounded_numeric_error():
    assert equivalent({"score": [1.0]}, {"score": [1.0 + 1e-7]})
    assert not equivalent({"score": [1.0]}, {"score": [1.001]})
    assert not equivalent({"score": [1.0]}, {"score": ["1.0"]})
    assert not equivalent({"score": [1.0]}, {"different": [1.0]})


def test_failed_artifact_cleanup_still_attempts_stack_deletion(monkeypatch):
    from experiments.data_api import __main__ as runner

    class S3:
        def delete_object(self, **kwargs):
            raise RuntimeError("Synthetic object deletion failure")

    class CloudFormation:
        deleted = False

        def delete_stack(self, **kwargs):
            self.deleted = True

        def describe_stacks(self, **kwargs):
            return {"Stacks": [{"StackStatus": "CREATE_COMPLETE"}]}

    cf = CloudFormation()
    monkeypatch.setattr(runner, "wait_stack", lambda *args, **kwargs: None)
    result = cleanup(cf, S3(), "owned-stack", {"Artifacts": "owned-bucket"}, "validation.zip")
    assert cf.deleted
    assert result["artifact"]["status"] == "failed"
    assert result["stack"]["status"] == "passed"
    assert result["status"] == "failed"


def test_cleanup_recognizes_automatic_deletion_without_redeleting():
    class CloudFormation:
        def describe_stacks(self, **kwargs):
            return {"Stacks": [{"StackStatus": "DELETE_COMPLETE"}]}

        def delete_stack(self, **kwargs):
            raise AssertionError("Do not re-delete a completed stack.")

    assert cleanup(CloudFormation(), object(), "owned-stack", {}, None)["status"] == "passed"


def test_auto_deleting_stack_does_not_wait_for_a_create_success():
    import pytest

    class CloudFormation:
        def describe_stacks(self, **kwargs):
            return {"Stacks": [{"StackStatus": "DELETE_IN_PROGRESS"}]}

    with pytest.raises(RuntimeError, match="automatic deletion"):
        wait_stack(CloudFormation(), "owned-stack")


def test_failed_status_read_does_not_prevent_stack_delete_attempt(monkeypatch):
    from experiments.data_api import __main__ as runner

    class CloudFormation:
        deleted = False

        def describe_stacks(self, **kwargs):
            raise ClientError({"Error": {"Code": "AccessDenied"}}, "DescribeStacks")

        def delete_stack(self, **kwargs):
            self.deleted = True

    cf = CloudFormation()
    monkeypatch.setattr(runner, "wait_stack", lambda *args, **kwargs: None)
    assert cleanup(cf, object(), "owned-stack", {}, None)["status"] == "passed"
    assert cf.deleted


def test_lambda_failure_preserves_fixture_diagnostic():
    import io

    import pytest

    from experiments.data_api.__main__ import invoke

    class Lambda:
        def invoke(self, **kwargs):
            return {
                "FunctionError": "Unhandled",
                "Payload": io.BytesIO(
                    json.dumps(
                        {"errorType": "SyntheticFailure", "errorMessage": "fixture diagnostic"}
                    ).encode()
                ),
            }

    with pytest.raises(RuntimeError, match="SyntheticFailure") as caught:
        invoke(Lambda(), "fixture", {})
    assert caught.value.validation_detail == "fixture diagnostic"


def test_readiness_waits_for_enablement_and_resume_but_not_denial(monkeypatch):
    import pytest

    from experiments.data_api.__main__ import resume_check

    monkeypatch.setattr("experiments.data_api.__main__.time.sleep", lambda seconds: None)

    class SQL:
        def __init__(self, code):
            self.code, self.calls = code, 0

        def query(self, statement):
            self.calls += 1
            if self.calls == 1:
                raise ClientError({"Error": {"Code": self.code}}, "ExecuteStatement")
            return [{"ready": 1}]

    for code in (
        "HttpEndpointNotEnabledException",
        "DatabaseResumingException",
        "DatabaseUnavailableException",
    ):
        sql = SQL(code)
        assert resume_check(sql)["status"] == "passed"
        assert sql.calls == 2
    denied = SQL("AccessDeniedException")
    with pytest.raises(ClientError):
        resume_check(denied)
    assert denied.calls == 1


def test_first_capacity_poll_has_a_nonempty_cloudwatch_window(monkeypatch):
    from datetime import UTC, datetime

    import pytest

    from experiments.data_api import __main__ as entrypoint

    fixed = datetime(2026, 11, 16, tzinfo=UTC)

    class Clock:
        @staticmethod
        def now(tz):
            return fixed

    class RequestChecked(Exception):
        pass

    class CloudWatch:
        def get_metric_statistics(self, **request):
            assert request["EndTime"] == fixed
            assert int(request["StartTime"].timestamp()) < int(request["EndTime"].timestamp())
            raise RequestChecked()

    monkeypatch.setattr(entrypoint, "datetime", Clock)
    with pytest.raises(RequestChecked):
        entrypoint.pause_check(CloudWatch(), "fixture", timeout=1)
