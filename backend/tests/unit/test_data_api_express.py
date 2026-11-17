import psycopg
import pytest

from experiments.data_api.express import database


def test_express_uses_verified_iam_admin_and_separate_password_user(monkeypatch):
    statements = []
    connections = []

    class Cursor:
        def __init__(self, query):
            self.query = query

        def fetchone(self):
            return (False,) if "pg_has_role" in self.query else ("postgres",)

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, query):
            query = query if isinstance(query, str) else query.as_string()
            statements.append(query)
            return Cursor(query)

    def connect(**kwargs):
        connections.append(kwargs)
        return Connection()

    monkeypatch.setattr(psycopg, "connect", connect)

    class Client:
        def get_secret_value(self, **kwargs):
            return {"SecretString": '{"username":"validator","password":"synthetic-only"}'}

        def generate_db_auth_token(self, **kwargs):
            assert kwargs["DBUsername"] == "postgres"
            return "synthetic-token"

    class Session:
        def client(self, *args):
            return Client()

    database(
        Session(), {"SecretArn": "fixture", "Host": "fixture.example.com"}, "data_api_" + "a" * 32
    )
    assert len(connections) == 2
    assert [connection["dbname"] for connection in connections] == ["postgres", "data_api_test"]
    assert all(
        connection["sslmode"] == "verify-full" and connection["sslrootcert"]
        for connection in connections
    )
    assert "GRANT validator TO postgres WITH SET TRUE" in statements
    assert statements.index("GRANT validator TO postgres WITH SET TRUE") < next(
        i for i, statement in enumerate(statements) if statement.startswith("CREATE SCHEMA")
    )
    assert connections[0]["password"] == "synthetic-token"
    assert "GRANT rds_iam TO baseline" in statements
    assert not any("GRANT rds_iam TO validator" in statement for statement in statements)
    assert any("CREATE ROLE validator LOGIN PASSWORD" in statement for statement in statements)
    assert any("GRANT SELECT ON TABLES TO baseline" in statement for statement in statements)


@pytest.mark.parametrize("expired", [False, True])
def test_express_connection_failure_retains_redacted_diagnostic(monkeypatch, capsys, expired):
    if expired:
        ticks = iter([0, 301])
        monkeypatch.setattr("experiments.data_api.express.time.monotonic", lambda: next(ticks))

    monkeypatch.setattr("experiments.data_api.express.time.sleep", lambda seconds: None)
    attempts = []

    def connect(**kwargs):
        attempts.append(kwargs)
        raise psycopg.OperationalError("fixture IAM-token connection refused")

    monkeypatch.setattr(psycopg, "connect", connect)

    class Client:
        def get_secret_value(self, **kwargs):
            return {"SecretString": '{"username":"validator","password":"synthetic-only"}'}

        def generate_db_auth_token(self, **kwargs):
            return "IAM-token"

    class Session:
        def client(self, *args):
            return Client()

    with pytest.raises(psycopg.OperationalError) as caught:
        database(
            Session(), {"SecretArn": "fixture", "Host": "fixture.example.com"}, "fixture_schema"
        )
    assert len(attempts) == (1 if expired else 150)
    assert "IAM-token" not in capsys.readouterr().out
    assert "IAM-token" not in caught.value.validation_detail
    assert "[redacted IAM token]" in caught.value.validation_detail
    assert "connection refused" in caught.value.validation_detail
    assert all(attempt["sslmode"] == "verify-full" for attempt in attempts)
