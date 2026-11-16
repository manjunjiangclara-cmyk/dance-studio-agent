"""Local PostgreSQL-backed protocol double; never evidence of live AWS compatibility."""

import json
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from psycopg.types.numeric import Int8

from experiments.data_api.sql import DirectSQL, parameter


class LocalDataClient:
    def __init__(self, connect):
        self.direct = DirectSQL(connect)
        self.connections = {}
        self.fail_part = False
        self.lose_commit = False
        self.max_row_bytes = 0

    def begin_transaction(self, **_kwargs):
        from psycopg.rows import dict_row

        connection = self.direct.connect()
        connection.row_factory = dict_row
        connection.execute("BEGIN")
        token = uuid4().hex
        self.connections[token] = connection
        return {"transactionId": token}

    def commit_transaction(self, *, transactionId, **_kwargs):
        connection = self.connections.pop(transactionId)
        try:
            connection.commit()
        finally:
            connection.close()
        if self.lose_commit:
            self.lose_commit = False
            raise TimeoutError("Synthetic acknowledgement loss after commit.")
        return {}

    def rollback_transaction(self, *, transactionId, **_kwargs):
        connection = self.connections.pop(transactionId, None)
        if connection:
            connection.rollback()
            connection.close()
        return {}

    def execute_statement(self, *, sql, parameters, transactionId=None, **_kwargs):
        if self.fail_part and "INSERT INTO" in sql and ".checkpoint_parts" in sql:
            self.fail_part = False
            raise RuntimeError("Synthetic partial write failure.")
        params = {}
        for p in parameters:
            value = p["value"]
            params[p["name"]] = None if value.get("isNull") else next(iter(value.values()))
            if "longValue" in value:
                # Data API binds all longValue parameters as PostgreSQL bigint.
                params[p["name"]] = Int8(value["longValue"])
        rows = self.direct.query(sql, params, tx=self.connections.get(transactionId))
        if not rows:
            return {"records": [], "columnMetadata": []}
        records = []
        for row in rows:
            fields = []
            for value in row.values():
                if isinstance(value, (date, datetime)):
                    value = value.isoformat()
                elif isinstance(value, (UUID, Decimal)):
                    value = str(value)
                elif isinstance(value, (dict, list)):
                    value = json.dumps(value)
                fields.append(parameter("ignored", value)["value"])
            size = len(json.dumps(fields, default=lambda x: x.hex()).encode())
            self.max_row_bytes = max(size, self.max_row_bytes)
            if size > 64 * 1024:
                raise ValueError("Synthetic Data API per-row limit.")
            records.append(fields)
        result = {"columnMetadata": [{"name": k} for k in rows[0]], "records": records}
        if len(json.dumps(result, default=lambda x: x.hex()).encode()) > 1024 * 1024:
            raise ValueError("Synthetic Data API response limit.")
        return result
