"""IAM-invoked validation handlers. No HTTP endpoint and no live model requests."""

import os
from uuid import UUID


def handler(event, _context):
    import boto3
    from botocore.config import Config

    from .fixtures import retrieve, stable
    from .probes import run
    from .sql import DataSQL, identifier

    if event.get("action") == "direct_baseline":
        from sqlalchemy import URL, create_engine
        from sqlalchemy.pool import NullPool

        schema = identifier(event["schema"])
        username = os.environ.get("DB_USER", "validator")
        if os.environ.get("DB_AUTH") == "iam":
            import certifi

            password = boto3.client("rds").generate_db_auth_token(
                DBHostname=os.environ["DB_HOST"],
                Port=5432,
                DBUsername=username,
            )
            tls = {"sslmode": "verify-full", "sslrootcert": certifi.where()}
        else:
            password = os.environ["DB_PASSWORD"]
            tls = {"sslmode": "require"}
        url = URL.create(
            "postgresql+psycopg",
            username=username,
            password=password,
            host=os.environ["DB_HOST"],
            database="data_api_test",
        )
        engine = create_engine(
            url,
            poolclass=NullPool,
            connect_args={**tls, "options": f"-csearch_path={schema},public"},
        )
        try:
            return {
                "status": "passed",
                "result": stable(retrieve(engine, [UUID(int=i + 11) for i in range(4)])),
            }
        finally:
            engine.dispose()
    if event.get("action") != "validate":
        raise ValueError("Unsupported experiment operation.")
    sql = DataSQL(
        boto3.client("rds-data", config=Config(retries={"total_max_attempts": 1})),
        os.environ["CLUSTER_ARN"],
        os.environ["SECRET_ARN"],
    )
    result = run(
        sql,
        identifier(event["schema"]),
        keep_schema=True,
        schema_exists=event.get("schema_exists", False),
    )
    result["data_api_calls"] = sql.calls
    result["max_response_bytes_estimated"] = sql.max_result_bytes
    result["non_vpc_lambda"] = True
    return result
