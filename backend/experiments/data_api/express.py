"""Express fixture initialization using exact-cluster IAM grants and verified TLS."""

import json
import subprocess
import time
from pathlib import Path


def permissions(resource_id, directory):
    root = Path(__file__).resolve().parents[3] / "infrastructure" / "bootstrap"
    plan = directory / "express-auth.tfplan"
    with (directory / "terraform.log").open("a") as log:
        subprocess.run(
            [
                "terraform",
                f"-chdir={root}",
                "plan",
                "-input=false",
                f"-var=express_cluster_resource_id={resource_id}",
                f"-out={plan}",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
        subprocess.run(
            ["terraform", f"-chdir={root}", "apply", "-input=false", str(plan)],
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )


def database(session, outputs, schema):
    import certifi
    import psycopg
    from psycopg import sql

    values = json.loads(
        session.client("secretsmanager").get_secret_value(SecretId=outputs["SecretArn"])[
            "SecretString"
        ]
    )
    assert values["username"] == "validator"
    rds = session.client("rds")
    for attempt in range(30):
        token = rds.generate_db_auth_token(
            DBHostname=outputs["Host"], Port=5432, DBUsername="postgres"
        )
        try:
            connection = psycopg.connect(
                host=outputs["Host"],
                user="postgres",
                password=token,
                dbname="postgres",
                sslmode="verify-full",
                sslrootcert=certifi.where(),
                connect_timeout=30,
                autocommit=True,
            )
            break
        except psycopg.OperationalError:
            if attempt == 29:
                raise
            time.sleep(2)

    def execute(connection, phase, statement):
        print(f"Express initialization: {phase}", flush=True)
        try:
            return connection.execute(statement)
        except psycopg.Error as error:
            error.validation_phase = phase
            raise

    with connection:
        execute(connection, "create_database", "CREATE DATABASE data_api_test")
    connection = psycopg.connect(
        host=outputs["Host"],
        user="postgres",
        password=token,
        dbname="data_api_test",
        sslmode="verify-full",
        sslrootcert=certifi.where(),
        connect_timeout=30,
        autocommit=True,
    )
    with connection:
        assert connection.execute("SELECT current_user").fetchone()[0] == "postgres"
        execute(
            connection,
            "create_vector_extension",
            "CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public",
        )
        execute(
            connection,
            "create_validator_role",
            sql.SQL("CREATE ROLE validator LOGIN PASSWORD {}").format(
                sql.Literal(values["password"])
            ),
        )
        execute(connection, "create_baseline_role", "CREATE ROLE baseline LOGIN")
        execute(connection, "grant_baseline_iam", "GRANT rds_iam TO baseline")
        # PostgreSQL 16+ grants creators ADMIN but not SET on newly created roles.
        # The initializer needs SET permission to assign schema ownership to validator.
        execute(connection, "grant_initializer_set", "GRANT validator TO postgres WITH SET TRUE")
        execute(
            connection,
            "create_fixture_schema",
            sql.SQL("CREATE SCHEMA {} AUTHORIZATION validator").format(sql.Identifier(schema)),
        )
        execute(
            connection,
            "grant_schema_usage",
            sql.SQL("GRANT USAGE ON SCHEMA {} TO baseline").format(sql.Identifier(schema)),
        )
        execute(
            connection,
            "grant_baseline_select",
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES FOR ROLE validator IN SCHEMA {} "
                "GRANT SELECT ON TABLES TO baseline"
            ).format(sql.Identifier(schema)),
        )
        assert not connection.execute(
            "SELECT pg_has_role('validator','rds_iam','MEMBER')"
        ).fetchone()[0]
