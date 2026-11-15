import pytest
from botocore.exceptions import ClientError

from experiments.data_api.delete_express import delete

NAME = "data-api-validation-" + "a" * 12


class Client:
    exists = True
    tags = {"Project": "dance-studio-agent", "Purpose": "data-api-validation"}

    def __init__(self):
        self.deleted = []

    def describe_db_clusters(self, **kwargs):
        if not self.exists:
            raise ClientError({"Error": {"Code": "DBClusterNotFoundFault"}}, "DescribeDBClusters")
        return {
            "DBClusters": [
                {
                    "DBClusterArn": "fixture-arn",
                    "Status": "available",
                    "DBClusterMembers": [{"DBInstanceIdentifier": NAME + "-writer"}],
                }
            ]
        }

    def list_tags_for_resource(self, **kwargs):
        return {"TagList": [{"Key": k, "Value": v} for k, v in self.tags.items()]}

    def describe_db_instances(self, **kwargs):
        return {"DBInstances": [{"DBInstanceStatus": "available"}]}

    def delete_db_instance(self, **kwargs):
        self.deleted.append(("instance", kwargs))

    def delete_db_cluster(self, **kwargs):
        self.deleted.append(("cluster", kwargs))
        self.exists = False


def test_cleanup_checks_ownership_and_uses_no_snapshot():
    client = Client()
    delete(client, NAME)
    assert [kind for kind, _ in client.deleted] == ["instance", "cluster"]
    assert all(options["SkipFinalSnapshot"] for _, options in client.deleted)
    delete(client, NAME)
    assert len(client.deleted) == 2


def test_cleanup_refuses_other_names_or_tags():
    client = Client()
    with pytest.raises(ValueError):
        delete(client, "production")
    client.tags = {}
    with pytest.raises(ValueError):
        delete(client, NAME)
    assert not client.deleted


def test_cleanup_waits_for_async_writer_and_retries_busy_cluster(monkeypatch):
    monkeypatch.setattr("experiments.data_api.delete_express.time.sleep", lambda seconds: None)

    class AsyncClient(Client):
        busy = True

        def delete_db_cluster(self, **kwargs):
            if self.busy:
                self.busy = False
                raise ClientError(
                    {"Error": {"Code": "InvalidDBClusterStateFault"}}, "DeleteDBCluster"
                )
            super().delete_db_cluster(**kwargs)

        def describe_db_instances(self, **kwargs):
            return {"DBInstances": [{"DBInstanceStatus": "available" if self.busy else "deleting"}]}

    client = AsyncClient()
    delete(client, NAME)
    assert [kind for kind, _ in client.deleted] == ["instance", "cluster"]


def test_cleanup_validates_all_members_before_any_mutation():
    class ForeignMember(Client):
        def describe_db_clusters(self, **kwargs):
            result = super().describe_db_clusters(**kwargs)
            result["DBClusters"][0]["DBClusterMembers"].append(
                {"DBInstanceIdentifier": "production"}
            )
            return result

    client = ForeignMember()
    with pytest.raises(ValueError, match="writer"):
        delete(client, NAME)
    assert not client.deleted


def test_cleanup_propagates_denied_delete_and_times_out(monkeypatch):
    monkeypatch.setattr("experiments.data_api.delete_express.time.sleep", lambda seconds: None)

    class Denied(Client):
        def delete_db_instance(self, **kwargs):
            raise ClientError({"Error": {"Code": "AccessDenied"}}, "DeleteDBInstance")

    with pytest.raises(ClientError):
        delete(Denied(), NAME)

    class Stuck(Client):
        def describe_db_clusters(self, **kwargs):
            result = super().describe_db_clusters(**kwargs)
            result["DBClusters"][0]["Status"] = "deleting"
            return result

    client = Stuck()
    with pytest.raises(TimeoutError):
        delete(client, NAME)
    assert not client.deleted
