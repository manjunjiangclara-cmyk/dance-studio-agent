import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
from sqlalchemy import create_engine, text

from experiments.data_api.fixtures import TEXTS, corpus, retrieve, stable
from experiments.data_api.leases import Leases, StaleOwner
from experiments.data_api.probes import checkpoint_probe, lease_probe
from experiments.data_api.retrieval import ReadEngine
from studio_copilot.documents.retrieval.engine import RetrievalError
from tests.integration.agent.test_data_api_checkpoint import data_api as data_api

pytestmark = pytest.mark.integration


def test_shared_lambda_mechanism_probes_pass_on_local_protocol(data_api):
    sql, schema, _ = data_api
    assert checkpoint_probe(sql, schema)["status"] == "passed"
    assert lease_probe(sql, schema)["status"] == "passed"


def test_hybrid_retrieval_matches_real_sqlalchemy_baseline(data_api, db_engine):
    sql, schema, _ = data_api
    runs = corpus(sql, schema)
    baseline = create_engine(
        db_engine.url, connect_args={"options": f"-csearch_path={schema},public"}
    )
    try:
        expected = stable(retrieve(baseline, runs))
    finally:
        baseline.dispose()
    actual = stable(retrieve(ReadEngine(sql, schema), runs))
    assert actual == expected
    assert len(actual["results"]) == 3
    assert actual["candidates"]["vector"][0]["score"] == 0
    assert actual["candidates"]["vector"][-1]["score"] == 1
    matching = next(r for r in actual["results"] if r["text"] == TEXTS[0])
    assert len(matching["other_sources"]) == 1
    assert actual["reported_tokens"] == 0


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("status='running'", "source_incomplete"),
        ("prepared=false", "source_incomplete"),
        ("profile_hash='wrong'", "profile_mismatch"),
    ],
)
def test_retrieval_keeps_source_validation(data_api, mutation, code):
    sql, schema, _ = data_api
    runs = corpus(sql, schema)
    sql.query(f"UPDATE {schema}.embedding_runs SET {mutation} WHERE id=:id", {"id": runs[0]})
    with pytest.raises(RetrievalError) as error:
        retrieve(ReadEngine(sql, schema), runs)
    assert error.value.code == code


def test_dates_archives_empty_and_multiple_runs(data_api):
    sql, schema, _ = data_api
    runs = corpus(sql, schema)
    engine = ReadEngine(sql, schema)
    with pytest.raises(RetrievalError, match="Select between"):
        retrieve(engine, [])
    assert not retrieve(engine, runs, as_of=date(2027, 2, 7))["results"]
    assert retrieve(engine, runs, as_of=date(2027, 2, 28))["results"]
    assert not retrieve(engine, runs, as_of=date(2027, 3, 1))["results"]
    sql.query(f"UPDATE {schema}.documents SET archived_at=clock_timestamp()")
    assert not retrieve(engine, runs)["results"]


def test_snapshot_does_not_mix_concurrent_source_update(data_api, monkeypatch):
    sql, schema, client = data_api
    runs = corpus(sql, schema)
    expected = stable(retrieve(ReadEngine(sql, schema), runs))
    execute = client.execute_statement
    updated = False

    def concurrent_change(**kwargs):
        nonlocal updated
        if "WITH refs AS" in kwargs["sql"] and not updated:
            updated = True
            sql.query(f"UPDATE {schema}.documents SET archived_at=clock_timestamp()")
        return execute(**kwargs)

    monkeypatch.setattr(client, "execute_statement", concurrent_change)
    actual = stable(retrieve(ReadEngine(sql, schema), runs))
    assert updated and actual == expected
    assert not retrieve(ReadEngine(sql, schema), runs)["results"]


def test_large_parent_reads_are_chunked_without_unicode_loss(data_api):
    sql, schema, client = data_api
    runs = corpus(sql, schema)
    content = "芭蕾💃" * 120_000
    assert len(content.encode()) > 1024 * 1024
    sql.query(
        f"UPDATE {schema}.document_chunks SET text=:text WHERE kind='parent'", {"text": content}
    )
    with ReadEngine(sql, schema).connect() as connection, connection.begin():
        row = (
            connection.execute(
                text("""SELECT chunk_id, parent_id, kind, text, provenance
            FROM document_chunks WHERE run_id=:run_id AND chunk_id=:chunk_id"""),
                {"run_id": runs[0], "chunk_id": "parent"},
            )
            .mappings()
            .one_or_none()
        )
    assert (
        hashlib.sha256(row["text"].encode()).digest() == hashlib.sha256(content.encode()).digest()
    )
    assert client.max_row_bytes < 64 * 1024 and sql.max_result_bytes < 1024 * 1024


def test_fenced_business_transaction_rolls_back_atomically(data_api):
    sql, schema, client = data_api
    leases = Leases(sql, schema)
    leases.setup()
    claim = leases.acquire("student", "worker")
    sql.query(f"CREATE TABLE {schema}.effects (id integer PRIMARY KEY)")
    with pytest.raises(RuntimeError):
        with leases.guard(claim) as tx:
            sql.query(f"INSERT INTO {schema}.effects VALUES (1)", tx=tx)
            raise RuntimeError("Crash before second business effect.")
    assert sql.query(f"SELECT id FROM {schema}.effects") == []
    client.lose_commit = True
    with pytest.raises(TimeoutError):
        leases.renew(claim)
    assert leases.acquire("student", "worker").token == claim.token
    assert leases.acquire("student", "another") is None


def test_renew_takeover_race_has_one_effective_owner(data_api):
    sql, schema, _ = data_api
    leases = Leases(sql, schema)
    leases.setup()
    old = leases.acquire("student", "old")
    sql.query(f"UPDATE {leases.table} SET expires_at=clock_timestamp()")

    def renew():
        try:
            leases.renew(old)
            return True
        except StaleOwner:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = pool.submit(renew)
        fresh = pool.submit(leases.acquire, "student", "new").result()
    assert result.result() is False
    assert fresh.token > old.token
