"""Executable mechanism probes shared by local protocol tests and live Lambda."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from langgraph.checkpoint.base import empty_checkpoint
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from studio_copilot.agent.contracts import State

from .checkpoints import DataAPISaver
from .fixtures import TEXTS, corpus, retrieve, stable
from .leases import Leases, StaleOwner
from .retrieval import ReadEngine
from .sql import identifier


def checkpoint_probe(sql, schema):
    def saver():
        item = DataAPISaver(sql, schema)
        item.setup()
        return item

    def graph():
        builder = StateGraph(State)
        builder.add_node("draft", lambda state: {"draft": {"body": "Teacher review. 芭蕾💃"}})

        def review(state):
            return {"decision": interrupt({"draft": state["draft"], "revision": 1})}

        builder.add_node("review", review)
        builder.add_edge(START, "draft")
        builder.add_edge("draft", "review")
        builder.add_edge("review", END)
        return builder.compile(checkpointer=saver())

    config = {"configurable": {"thread_id": "typed-interrupt"}}
    graph().invoke({"run_id": "synthetic-run"}, config)
    assert graph().get_state(config).tasks[0].interrupts
    graph().invoke(Command(resume={"action": "approve", "body": "Approved."}), config)
    assert graph().get_state(config).values["decision"]["action"] == "approve"
    large = empty_checkpoint()
    large["channel_values"] = {"body": "芭蕾💃" * 100_000, "binary": b"\x00\xff" * 40_000}
    config = {"configurable": {"thread_id": "large"}}
    saved = saver().put(config, large, {"step": 1}, {})
    saver().put(config, large, {"step": 1}, {})
    saver().put_writes(saved, [("draft", "first")], "task")
    saver().put_writes(saved, [("draft", "second")], "task")
    recovered = saver().get_tuple(saved)
    assert recovered.checkpoint == large
    assert recovered.pending_writes == [("task", "draft", "first")]
    return {
        "status": "passed",
        "scope": "typed State interrupt and saver mechanisms",
        "actual_application_workflow": "covered separately by local integration tests",
    }


def lease_probe(sql, schema):
    leases = Leases(sql, schema)
    leases.setup()
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda owner: leases.acquire("student", owner), ["a", "b"]))
    assert sum(c is not None for c in claims) == 1
    old = next(c for c in claims if c is not None)
    assert leases.acquire("different-student", "c") is not None
    assert leases.acquire(old.key, old.owner).token == old.token
    # Force expiry using database time: deterministic takeover without a sleep.
    sql.query(
        f"UPDATE {leases.table} SET expires_at=clock_timestamp() WHERE key=:key", {"key": old.key}
    )
    fresh = leases.acquire("student", "new")
    assert fresh.token > old.token
    for operation in (leases.renew, leases.release):
        try:
            operation(old)
        except StaleOwner:
            pass
        else:
            raise AssertionError("Stale worker changed a lease.")
    sql.query(f"CREATE TABLE {schema}.business_effects (id text PRIMARY KEY)")
    for _ in range(2):
        with leases.guard(fresh) as tx:
            sql.query(
                f"INSERT INTO {schema}.business_effects VALUES ('response') ON CONFLICT DO NOTHING",
                tx=tx,
            )
    try:
        with leases.guard(old) as tx:
            sql.query(f"INSERT INTO {schema}.business_effects VALUES ('stale')", tx=tx)
    except StaleOwner:
        pass
    else:
        raise AssertionError("Stale worker committed a business mutation.")
    saver = DataAPISaver(sql, schema, leases=leases, claim=old)
    saver.setup()
    try:
        saver.put({"configurable": {"thread_id": "stale"}}, empty_checkpoint(), {}, {})
    except StaleOwner:
        pass
    else:
        raise AssertionError("Stale worker published a checkpoint.")
    assert sql.query(f"SELECT id FROM {schema}.business_effects") == [{"id": "response"}]
    return {"status": "passed", "scope": "atomic lease, mutation and checkpoint fencing"}


def retrieval_probe(sql, schema):
    runs = corpus(sql, schema)
    result = retrieve(ReadEngine(sql, schema), runs)
    hashes = sorted(hashlib.sha256(text.encode()).hexdigest() for text in TEXTS)
    assert sorted(r["text_sha256"] for r in result["results"]) == hashes
    first_hash = hashlib.sha256(TEXTS[0].encode()).hexdigest()
    duplicate = next(r for r in result["results"] if r["text_sha256"] == first_hash)
    assert len(duplicate["other_sources"]) == 1
    assert result["reported_tokens"] == 0
    return {
        "status": "passed",
        "scope": "real application hybrid search, fixture expectations",
        "result": stable(result),
    }


def run(sql, schema=None, *, keep_schema=False, schema_exists=False):
    schema = identifier(schema or "data_api_" + uuid4().hex)
    report = {"schema": schema, "openai_calls": 0, "checks": {}, "status": "failed"}
    if not schema_exists:
        sql.query(f"CREATE SCHEMA {schema}")
    try:
        sql.query("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public")
        report["engine"] = sql.query("SELECT version() AS version")[0]["version"]
        report["vector"] = sql.query("SELECT extversion FROM pg_extension WHERE extname='vector'")[
            0
        ]
        for name, probe in (
            ("checkpoint", checkpoint_probe),
            ("mutex", lease_probe),
            ("retrieval", retrieval_probe),
        ):
            try:
                report["checks"][name] = probe(sql, schema)
            except Exception as error:
                report["checks"][name] = {
                    "status": "failed",
                    "error_type": type(error).__name__,
                    # Probe SQL and values are exclusively fictional fixtures.
                    "reason": str(error)[:1000],
                }
        report["status"] = (
            "passed"
            if all(r["status"] == "passed" for r in report["checks"].values())
            else "failed"
        )
        return report
    finally:
        if not keep_schema:
            sql.query(f"DROP SCHEMA {schema} CASCADE")
