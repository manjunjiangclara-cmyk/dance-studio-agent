"""Small explicit SQL transport. No connection/session emulation or implicit retries."""

import json
import re
from contextlib import contextmanager
from datetime import date, datetime
from uuid import UUID


def identifier(value):
    if not re.fullmatch(r"data_api_[a-f0-9]{32}", value):
        raise ValueError("Use a randomly generated, experiment-owned schema.")
    return value


def parameter(name, value):
    result = {"name": name}
    if value is None:
        field = {"isNull": True}
    elif isinstance(value, bool):
        field = {"booleanValue": value}
    elif isinstance(value, int):
        field = {"longValue": value}
    elif isinstance(value, float):
        field = {"doubleValue": value}
    elif isinstance(value, bytes):
        field = {"blobValue": value}
    else:
        if isinstance(value, (dict, list)):
            value = json.dumps(value, default=str, ensure_ascii=False)
            result["typeHint"] = "JSON"
        elif isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, date):
            value = value.isoformat()
            result["typeHint"] = "DATE"
        elif isinstance(value, UUID):
            value = str(value)
            result["typeHint"] = "UUID"
        elif not isinstance(value, str):
            raise TypeError("Unsupported Data API parameter type.")
        field = {"stringValue": value}
    return {**result, "value": field}


def decode(field):
    if field == {"isNull": True}:
        return None
    if len(field) != 1:
        raise ValueError("Malformed Data API field.")
    key, value = next(iter(field.items()))
    if key not in {"stringValue", "longValue", "doubleValue", "booleanValue", "blobValue"}:
        raise ValueError("Unsupported Data API result field.")
    return value


class DataSQL:
    def __init__(self, client, cluster, secret, database="data_api_test"):
        self.client = client
        self.options = {"resourceArn": cluster, "secretArn": secret, "database": database}
        self.calls = 0
        self.max_result_bytes = 0

    def query(self, sql, parameters=None, *, tx=None):
        options = dict(self.options)
        if tx:
            options["transactionId"] = tx
        self.calls += 1
        response = self.client.execute_statement(
            **options,
            sql=sql,
            parameters=[
                parameter(k, v)
                for k, v in (parameters or {}).items()
                if k in re.findall(r"(?<!:):([a-zA-Z_]\w*)", sql)
            ],
            includeResultMetadata=True,
        )
        self.max_result_bytes = max(
            self.max_result_bytes,
            len(json.dumps(response, default=lambda x: x.hex()).encode()),
        )
        names = [c["name"] for c in response.get("columnMetadata", [])]
        rows = response.get("records", [])
        if any(len(row) != len(names) for row in rows):
            raise ValueError("Malformed Data API result metadata.")
        return [dict(zip(names, map(decode, row), strict=True)) for row in rows]

    @contextmanager
    def transaction(self, *, readonly=False):
        self.calls += 1
        tx = self.client.begin_transaction(**self.options)["transactionId"]
        try:
            if readonly:
                self.query("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY", tx=tx)
            yield tx
            self.calls += 1
            self.client.commit_transaction(
                resourceArn=self.options["resourceArn"],
                secretArn=self.options["secretArn"],
                transactionId=tx,
            )
        except BaseException:
            self.calls += 1
            try:
                self.client.rollback_transaction(
                    resourceArn=self.options["resourceArn"],
                    secretArn=self.options["secretArn"],
                    transactionId=tx,
                )
            except Exception:
                # Preserve the original failure, including an uncertain commit acknowledgement.
                pass
            raise


class DirectSQL:
    """Independent psycopg transport used only for baseline/protocol tests."""

    def __init__(self, connect):
        self.connect = connect

    def query(self, sql, parameters=None, *, tx=None):
        from psycopg.rows import dict_row

        sql = re.sub(r"(?<!:):([a-zA-Z_]\w*)", r"%(\1)s", sql)
        params = {
            k: json.dumps(v, default=str) if isinstance(v, (list, dict)) else v
            for k, v in (parameters or {}).items()
        }
        if tx is not None:
            cursor = tx.execute(sql, params)
            return cursor.fetchall() if cursor.description else []
        with self.connect() as connection:
            connection.row_factory = dict_row
            cursor = connection.execute(sql, params)
            return cursor.fetchall() if cursor.description else []

    @contextmanager
    def transaction(self, *, readonly=False):
        from psycopg.rows import dict_row

        with self.connect() as connection:
            connection.row_factory = dict_row
            with connection.transaction():
                if readonly:
                    connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                yield connection
