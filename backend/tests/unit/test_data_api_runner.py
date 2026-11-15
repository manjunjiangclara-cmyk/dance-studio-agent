import json

import boto3
from botocore.exceptions import ClientError

from experiments.data_api.__main__ import cleanup, equivalent, live
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

    cf = CloudFormation()
    monkeypatch.setattr(runner, "wait_stack", lambda *args, **kwargs: None)
    result = cleanup(cf, S3(), "owned-stack", {"Artifacts": "owned-bucket"}, "validation.zip")
    assert cf.deleted
    assert result["artifact"]["status"] == "failed"
    assert result["stack"]["status"] == "passed"
    assert result["status"] == "failed"
