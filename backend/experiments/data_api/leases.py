"""Database-time leases; ownership checks and protected writes share one transaction."""

from contextlib import contextmanager
from dataclasses import dataclass

from .sql import identifier


class StaleOwner(Exception):
    pass


@dataclass(frozen=True)
class Claim:
    key: str
    owner: str
    token: int


class Leases:
    def __init__(self, sql, schema):
        self.sql, self.table = sql, f"{identifier(schema)}.leases"

    def setup(self):
        self.sql.query(f"""CREATE TABLE IF NOT EXISTS {self.table} (
            key text PRIMARY KEY, owner text NOT NULL, token bigint NOT NULL,
            expires_at timestamptz NOT NULL)""")

    def acquire(self, key, owner, *, seconds=90):
        if not 1 <= seconds <= 900:
            raise ValueError("Lease duration must be 1–900 seconds.")
        rows = self.sql.query(
            f"""INSERT INTO {self.table} AS l VALUES
            (:key, :owner, 1, clock_timestamp() + :seconds * interval '1 second')
            ON CONFLICT (key) DO UPDATE SET owner = EXCLUDED.owner,
            token = CASE WHEN l.owner = :owner AND l.expires_at > clock_timestamp()
                         THEN l.token ELSE l.token + 1 END,
            expires_at = EXCLUDED.expires_at
            WHERE l.expires_at <= clock_timestamp() OR l.owner = :owner
            RETURNING token""",
            dict(key=key, owner=owner, seconds=seconds),
        )
        return Claim(key, owner, rows[0]["token"]) if rows else None

    def _check(self, claim, tx):
        rows = self.sql.query(
            f"""SELECT token FROM {self.table} WHERE key=:key AND owner=:owner
            AND token=:token AND expires_at > clock_timestamp() FOR UPDATE""",
            vars(claim),
            tx=tx,
        )
        if not rows:
            raise StaleOwner("This worker no longer owns the task.")

    @contextmanager
    def guard(self, claim):
        with self.sql.transaction() as tx:
            self._check(claim, tx)
            yield tx

    def renew(self, claim, *, seconds=90):
        if not 1 <= seconds <= 900:
            raise ValueError("Lease duration must be 1–900 seconds.")
        with self.guard(claim) as tx:
            self.sql.query(
                f"""UPDATE {self.table} SET expires_at =
                clock_timestamp() + :seconds * interval '1 second' WHERE key=:key""",
                dict(key=claim.key, seconds=seconds),
                tx=tx,
            )

    def release(self, claim):
        with self.guard(claim) as tx:
            self.sql.query(
                f"UPDATE {self.table} SET expires_at=clock_timestamp() WHERE key=:key",
                dict(key=claim.key),
                tx=tx,
            )
