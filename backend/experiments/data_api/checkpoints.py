"""Experimental synchronous LangGraph saver with atomic, bounded binary chunks.

Full channel values are stored with each checkpoint. This intentionally trades storage
efficiency for a small auditable prototype; it is not a replacement PostgresSaver.
"""

import hashlib
from contextlib import contextmanager

from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    BaseCheckpointSaver,
    CheckpointTuple,
    get_checkpoint_metadata,
    writes_sort_key,
)

from .sql import identifier

CHUNK_BYTES = 16 * 1024


class DataAPISaver(BaseCheckpointSaver):
    def __init__(self, sql, schema, *, leases=None, claim=None):
        super().__init__()
        if (leases is None) != (claim is None):
            raise ValueError("Supply both leases and claim, or neither.")
        self.sql, self.schema, self.leases, self.claim = sql, identifier(schema), leases, claim
        self.heads, self.parts = f"{schema}.checkpoint_objects", f"{schema}.checkpoint_parts"

    def setup(self):
        self.sql.query(f"""CREATE TABLE IF NOT EXISTS {self.heads} (
            thread_id text NOT NULL, ns text NOT NULL, id text NOT NULL, slot text NOT NULL,
            type text NOT NULL, count integer NOT NULL, sha256 text NOT NULL, parent text,
            PRIMARY KEY (thread_id, ns, id, slot))""")
        self.sql.query(f"""CREATE TABLE IF NOT EXISTS {self.parts} (
            thread_id text NOT NULL, ns text NOT NULL, id text NOT NULL, slot text NOT NULL,
            part integer NOT NULL, data bytea NOT NULL,
            PRIMARY KEY (thread_id, ns, id, slot, part),
            FOREIGN KEY (thread_id, ns, id, slot)
                REFERENCES {self.heads} ON DELETE CASCADE)""")

    @contextmanager
    def _write(self):
        if self.leases is not None:
            with self.leases.guard(self.claim) as tx:
                yield tx
        else:
            with self.sql.transaction() as tx:
                yield tx

    @staticmethod
    def _keys(config, checkpoint_id=None):
        c = config["configurable"]
        return dict(
            thread_id=c["thread_id"],
            ns=c.get("checkpoint_ns", ""),
            id=checkpoint_id or c.get("checkpoint_id"),
        )

    def _save(self, keys, slot, value, tx, *, parent=None, overwrite=False):
        kind, data = self.serde.dumps_typed(value)
        chunks = [data[i : i + CHUNK_BYTES] for i in range(0, len(data), CHUNK_BYTES)] or [b""]
        params = dict(
            **keys,
            slot=slot,
            type=kind,
            count=len(chunks),
            sha256=hashlib.sha256(data).hexdigest(),
            parent=parent,
        )
        created = self.sql.query(
            f"""INSERT INTO {self.heads} VALUES
            (:thread_id,:ns,:id,:slot,:type,:count,:sha256,:parent)
            ON CONFLICT DO NOTHING RETURNING id""",
            params,
            tx=tx,
        )
        condition = "thread_id=:thread_id AND ns=:ns AND id=:id AND slot=:slot"
        if not created:
            existing = self.sql.query(
                f"SELECT sha256 FROM {self.heads} WHERE {condition} FOR UPDATE", params, tx=tx
            )[0]
            if existing["sha256"] == params["sha256"]:
                return
            if not overwrite:
                if slot.startswith("write:"):
                    return  # Regular pending writes use first-write-wins, like PostgresSaver.
                raise ValueError("Checkpoint identity was reused for different contents.")
            self.sql.query(f"DELETE FROM {self.parts} WHERE {condition}", params, tx=tx)
            self.sql.query(
                f"""UPDATE {self.heads} SET type=:type, count=:count, sha256=:sha256
                WHERE {condition}""",
                params,
                tx=tx,
            )
        for part, chunk in enumerate(chunks):
            self.sql.query(
                f"""INSERT INTO {self.parts} VALUES
                (:thread_id,:ns,:id,:slot,:part,:data)""",
                dict(**keys, slot=slot, part=part, data=chunk),
                tx=tx,
            )

    def _load(self, keys, slot, tx):
        params = dict(**keys, slot=slot)
        condition = "thread_id=:thread_id AND ns=:ns AND id=:id AND slot=:slot"
        heads = self.sql.query(f"SELECT * FROM {self.heads} WHERE {condition}", params, tx=tx)
        if not heads:
            raise ValueError("Checkpoint object is missing.")
        head, data = heads[0], bytearray()
        for start in range(0, head["count"], 16):
            parts = self.sql.query(
                f"""SELECT part,data FROM {self.parts} WHERE {condition}
                AND part>=:start AND part<:end ORDER BY part""",
                dict(**params, start=start, end=min(start + 16, head["count"])),
                tx=tx,
            )
            if [r["part"] for r in parts] != list(range(start, min(start + 16, head["count"]))):
                raise ValueError("Checkpoint chunks are incomplete.")
            for part in parts:
                data.extend(part["data"])
        if hashlib.sha256(data).hexdigest() != head["sha256"]:
            raise ValueError("Checkpoint checksum does not match.")
        return self.serde.loads_typed((head["type"], bytes(data)))

    def put(self, config, checkpoint, metadata, new_versions):
        keys = self._keys(config, checkpoint["id"])
        with self._write() as tx:
            self._save(
                keys,
                "checkpoint",
                checkpoint,
                tx,
                parent=config["configurable"].get("checkpoint_id"),
            )
            self._save(keys, "metadata", get_checkpoint_metadata(config, metadata), tx)
        return {
            "configurable": {
                "thread_id": keys["thread_id"],
                "checkpoint_ns": keys["ns"],
                "checkpoint_id": keys["id"],
            }
        }

    def put_writes(self, config, writes, task_id, task_path=""):
        keys = self._keys(config)
        with self._write() as tx:
            for index, (channel, value) in enumerate(writes):
                index = WRITES_IDX_MAP.get(channel, index)
                self._save(
                    keys,
                    f"write:{task_id}:{index}",
                    (task_id, channel, value, task_path),
                    tx,
                    overwrite=index < 0,
                )

    def get_tuple(self, config):
        keys = self._keys(config)
        with self.sql.transaction(readonly=True) as tx:
            predicate = "AND id=:id" if keys["id"] else ""
            rows = self.sql.query(
                f"""SELECT id,parent FROM {self.heads} WHERE thread_id=:thread_id
                AND ns=:ns AND slot='checkpoint' {predicate} ORDER BY id DESC LIMIT 1""",
                keys,
                tx=tx,
            )
            if not rows:
                return None
            keys["id"] = rows[0]["id"]
            result_config = {
                "configurable": dict(
                    thread_id=keys["thread_id"], checkpoint_ns=keys["ns"], checkpoint_id=keys["id"]
                )
            }
            pending, after = [], ""
            while True:
                slots = self.sql.query(
                    f"""SELECT slot FROM {self.heads} WHERE thread_id=:thread_id AND ns=:ns
                    AND id=:id AND starts_with(slot,'write:') AND slot>:after
                    ORDER BY slot LIMIT 50""",
                    dict(**keys, after=after),
                    tx=tx,
                )
                for slot in slots:
                    task, channel, value, path = self._load(keys, slot["slot"], tx)
                    index = int(slot["slot"].rsplit(":", 1)[1])
                    pending.append((writes_sort_key(path, task, index), (task, channel, value)))
                if len(slots) < 50:
                    break
                after = slots[-1]["slot"]
            parent = rows[0]["parent"]
            return CheckpointTuple(
                config=result_config,
                checkpoint=self._load(keys, "checkpoint", tx),
                metadata=self._load(keys, "metadata", tx),
                parent_config={
                    "configurable": {
                        **result_config["configurable"],
                        "checkpoint_id": parent,
                    }
                }
                if parent
                else None,
                pending_writes=[value for _, value in sorted(pending, key=lambda item: item[0])],
            )

    def list(self, config, *, filter=None, before=None, limit=None):
        if config is None:
            raise ValueError("Experiment requires an explicit thread.")
        keys = self._keys(config)
        cursor = (before or {}).get("configurable", {}).get("checkpoint_id", "")
        count = 0
        while limit is None or count < limit:
            predicate = "AND id<:before" if cursor else ""
            rows = self.sql.query(
                f"""SELECT id FROM {self.heads} WHERE thread_id=:thread_id AND ns=:ns
                AND slot='checkpoint' {predicate} ORDER BY id DESC LIMIT 50""",
                dict(**keys, before=cursor),
            )
            if not rows:
                return
            for row in rows:
                item = self.get_tuple(
                    {
                        "configurable": {
                            **config["configurable"],
                            "checkpoint_id": row["id"],
                        }
                    }
                )
                if item is not None and all(
                    item.metadata.get(k) == v for k, v in (filter or {}).items()
                ):
                    yield item
                    count += 1
                    if limit is not None and count >= limit:
                        return
            cursor = rows[-1]["id"]

    def delete_thread(self, thread_id):
        with self._write() as tx:
            self.sql.query(
                f"DELETE FROM {self.heads} WHERE thread_id=:thread_id",
                dict(thread_id=thread_id),
                tx=tx,
            )
