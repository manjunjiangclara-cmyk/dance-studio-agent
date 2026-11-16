"""Narrow read adapter for the unchanged application hybrid retrieval implementation.

This deliberately does not pretend to implement a general SQLAlchemy dialect.
"""

import json
import re
from contextlib import contextmanager
from datetime import date
from uuid import UUID

from .sql import identifier

TABLES = (
    "document_chunks",
    "embedding_runs",
    "documents",
    "document_revisions",
    "embedding_vectors",
)


def statement(sql, schema):
    schema = identifier(schema)
    for name in ("run_ids", "hashes", "heading_ids"):
        kind = "uuid" if name == "run_ids" else "text"
        sql = sql.replace(
            f"ANY(:{name})",
            f"ANY(ARRAY(SELECT jsonb_array_elements_text(CAST(:{name} AS jsonb)))::{kind}[])",
        )
    for table in TABLES:
        sql = re.sub(rf"(?<![\w.]){table}\b", f"{schema}.{table}", sql)
    return sql


def normalize(row):
    result = dict(row)
    for key, value in row.items():
        if value is None:
            continue
        if key in {"profile", "warnings", "provenance", "source_spans", "coalesce"}:
            result[key] = json.loads(value) if isinstance(value, str) else value
        elif key in {"run_id", "document_id"}:
            result[key] = UUID(str(value))
        elif key in {"effective_from", "effective_to"} and isinstance(value, str):
            result[key] = date.fromisoformat(value)
    return result


class Rows:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def one_or_none(self):
        if len(self.rows) > 1:
            raise ValueError("Expected at most one row.")
        return self.rows[0] if self.rows else None

    def __iter__(self):
        return iter(self.rows)


class ReadEngine:
    def __init__(self, sql, schema):
        self.sql, self.schema = sql, identifier(schema)

    def connect(self):
        return ReadConnection(self.sql, self.schema)


class ReadConnection:
    def __init__(self, sql, schema):
        self.sql, self.schema, self.tx = sql, schema, None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execution_options(self, *, isolation_level):
        if isolation_level != "REPEATABLE READ":
            raise ValueError("Only the retrieval snapshot isolation is supported.")
        return self

    @contextmanager
    def begin(self):
        with self.sql.transaction(readonly=True) as tx:
            self.tx = tx
            try:
                yield self
            finally:
                self.tx = None

    def execute(self, sql, parameters=None):
        if self.tx is None:
            raise ValueError("Retrieval reads require an explicit snapshot.")
        sql = str(sql)
        if sql.strip() == "SET TRANSACTION READ ONLY":
            return Rows([])  # Already set by transaction(readonly=True).
        chunk = "SELECT chunk_id, parent_id, kind, text, provenance" in sql
        if chunk:
            sql = sql.replace("kind, text, provenance", "kind, '' AS text, provenance")
        rows = self.sql.query(statement(sql, self.schema), parameters, tx=self.tx)
        if chunk:
            for row in rows:
                pieces, offset = [], 1
                while True:
                    piece = self.sql.query(
                        f"""SELECT substring(text FROM CAST(:offset AS integer) FOR 4096) AS piece
                        FROM {self.schema}.document_chunks
                        WHERE run_id=:run_id AND chunk_id=:chunk_id""",
                        dict(**parameters, offset=offset),
                        tx=self.tx,
                    )[0]["piece"]
                    pieces.append(piece)
                    if len(piece) < 4096:
                        break
                    offset += 4096
                row["text"] = "".join(pieces)
        return Rows([normalize(row) for row in rows])

    def scalar(self, sql, parameters=None):
        rows = list(self.execute(sql, parameters))
        return next(iter(rows[0].values())) if rows else None
