"""Read-only exact/keyword retrieval with explicit corpus and bounded context."""

import json
import time
from contextlib import contextmanager
from datetime import date
from uuid import UUID

from sqlalchemy import text

from studio_copilot.documents.embedding.provider import (
    Embedder,
    EmbeddingError,
    EmbeddingProfile,
    validate_vector,
)

VERSION = "retrieval-v1"
CANDIDATES = 20
RESULTS = 6
BUDGET = 12_000
# Every search, duplicate reference, and parent read uses these same restrictions.
ELIGIBLE = """
 FROM document_chunks c
 JOIN embedding_runs r ON r.id = c.run_id
 JOIN document_revisions d ON d.document_id = r.document_id AND d.revision = r.revision
 WHERE c.run_id = ANY(:run_ids) AND r.status = 'complete'
 AND c.kind = 'passage' AND c.vector_key IS NOT NULL
 AND d.ingestion_status = 'ready'
 AND (d.effective_from IS NULL OR d.effective_from <= :as_of)
 AND (d.effective_to IS NULL OR d.effective_to >= :as_of)
"""
KEYWORD_SQL = (
    """
 WITH scored AS (
 SELECT c.text_sha256, ts_rank_cd(to_tsvector('english'::regconfig, c.text),
 websearch_to_tsquery('english'::regconfig, :query)) AS score
 """
    + ELIGIBLE
    + """
 AND to_tsvector('english'::regconfig, c.text) @@
 websearch_to_tsquery('english'::regconfig, :query)
 ), unique_inputs AS (
 SELECT text_sha256, max(score) AS score FROM scored GROUP BY text_sha256
 ) SELECT * FROM unique_inputs ORDER BY score DESC, text_sha256 LIMIT 20
"""
)
VECTOR_SQL = (
    """
 WITH inputs AS MATERIALIZED (
 SELECT DISTINCT c.vector_key, c.text_sha256
 """
    + ELIGIBLE
    + """
 ) SELECT i.text_sha256, v.embedding <=> CAST(:query_vector AS public.vector) AS score
 FROM inputs i JOIN embedding_vectors v ON v.key = i.vector_key
 ORDER BY score, i.text_sha256 LIMIT 20
"""
)
REFERENCES_SQL = (
    """
 WITH refs AS (
 SELECT c.run_id, c.chunk_id, c.parent_id, c.text_sha256,
 c.provenance->'source_spans' AS source_spans,
 r.document_id, r.revision, d.title, d.effective_from, d.effective_to,
 row_number() OVER (PARTITION BY c.text_sha256 ORDER BY
 r.document_id, r.revision, c.ordinal, c.chunk_id) AS source_rank,
 count(*) OVER (PARTITION BY c.text_sha256) AS total_sources
 """
    + ELIGIBLE
    + """
 AND c.text_sha256 = ANY(:hashes)
 ) SELECT * FROM refs WHERE source_rank <= 4 ORDER BY text_sha256, source_rank
"""
)


class RetrievalError(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


@contextmanager
def snapshot(engine):
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        with connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            yield connection


def _sources(connection, run_ids, as_of):
    rows = (
        connection.execute(
            text("""
        SELECT r.id AS run_id, r.document_id, r.revision, r.status, r.prepared,
        r.profile_hash, r.profile, r.warnings, d.sha256, d.title,
        d.effective_from, d.effective_to, d.ingestion_status,
        (d.effective_from IS NULL OR d.effective_from <= :as_of) AND
        (d.effective_to IS NULL OR d.effective_to >= :as_of) AS applicable
        FROM embedding_runs r JOIN document_revisions d
        ON d.document_id = r.document_id AND d.revision = r.revision
        WHERE r.id = ANY(:run_ids) ORDER BY r.id
        """),
            dict(run_ids=run_ids, as_of=as_of),
        )
        .mappings()
        .all()
    )
    if len(rows) != len(run_ids):
        raise RetrievalError("source_missing", "A selected embedding run no longer exists.")
    if any(
        r["status"] != "complete" or not r["prepared"] or r["ingestion_status"] != "ready"
        for r in rows
    ):
        raise RetrievalError(
            "source_incomplete", "Select complete runs of valid document revisions."
        )
    if len({r["document_id"] for r in rows}) != len(rows):
        raise RetrievalError("source_conflict", "Select only one run/revision per document.")
    if len({r["profile_hash"] for r in rows}) != 1:
        raise RetrievalError(
            "profile_mismatch", "Selected runs use incompatible embedding profiles."
        )
    try:
        profile = EmbeddingProfile(**rows[0]["profile"])
    except (ValueError, TypeError):
        raise RetrievalError(
            "profile_mismatch", "The stored embedding profile is invalid."
        ) from None
    if any(r["profile_hash"] != profile.key or r["profile"] != rows[0]["profile"] for r in rows):
        raise RetrievalError(
            "profile_mismatch", "Stored embedding profile identity does not match."
        )
    return rows, profile


def fuse(keyword, vector):
    """RRF merges existing retrieval ranks; it is not a learned reranking stage."""
    combined = {}
    for route, candidates in (("keyword", keyword), ("vector", vector)):
        for rank, row in enumerate(candidates, 1):
            key = row["text_sha256"]
            value = combined.setdefault(
                key,
                dict(
                    text_sha256=key,
                    keyword_rank=None,
                    vector_rank=None,
                    keyword_score=None,
                    cosine_distance=None,
                    rrf_score=0.0,
                ),
            )
            value[route + "_rank"] = rank
            value["keyword_score" if route == "keyword" else "cosine_distance"] = float(
                row["score"]
            )
            value["rrf_score"] += 1 / (60 + rank)
    return sorted(combined.values(), key=lambda r: (-r["rrf_score"], r["text_sha256"]))


def _chunk(connection, run_id, chunk_id):
    row = (
        connection.execute(
            text("""
        SELECT chunk_id, parent_id, kind, text, provenance FROM document_chunks
        WHERE run_id = :run_id AND chunk_id = :chunk_id
        """),
            dict(run_id=run_id, chunk_id=chunk_id),
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise RetrievalError("invalid_chunks", "A selected passage/context chunk is missing.")
    return dict(row)


def pack_evidence(connection, results, tokenizer):
    evidence = [
        dict(
            run_id=r["run_id"],
            chunk_id=r["chunk_id"],
            parent_id=r["parent_id"],
            kind="passage",
            source_spans=r["source_spans"],
            prefix=r["prefix"],
            text=r["text"],
        )
        for r in results
    ]
    warnings = []
    seen = set()
    for hit in results:
        parent_id = hit["parent_id"]
        key = (hit["run_id"], parent_id)
        if not parent_id or key in seen:
            continue
        seen.add(key)
        parent = _chunk(connection, UUID(hit["run_id"]), parent_id)
        if parent["kind"] != "parent":
            raise RetrievalError("invalid_chunks", "Passage context is not a parent chunk.")
        item = dict(
            run_id=hit["run_id"],
            chunk_id=parent_id,
            parent_id=parent_id,
            kind="parent",
            source_spans=parent["provenance"]["source_spans"],
            prefix=parent["provenance"].get("prefix", ""),
            text=parent["text"],
        )
        # Replace every selected passage covered by this parent at its first position.
        indices = [i for i, e in enumerate(evidence) if (e["run_id"], e["parent_id"]) == key]
        proposed = [e for i, e in enumerate(evidence) if i not in indices]
        proposed.insert(indices[0], item)
        if tokenizer.count("\n\n".join(e["text"] for e in proposed)) <= BUDGET:
            evidence = proposed
        else:
            warnings.append("parent_context_budget_limited")
    count = tokenizer.count("\n\n".join(e["text"] for e in evidence))
    if count > BUDGET:
        raise RetrievalError("invalid_chunks", "Retrieved passages exceed the evidence budget.")
    return evidence, count, sorted(set(warnings))


def search(
    engine, run_ids, query, as_of, tokenizer, *, mode="hybrid", allow_api=False, embedder=None
):
    started = time.perf_counter()
    if not isinstance(query, str) or not query.strip() or len(query) > 4096 or "\x00" in query:
        raise RetrievalError(
            "invalid_query", "Provide a nonempty question of at most 4096 characters, without NUL."
        )
    query_tokens = tokenizer.count(query)
    if query_tokens > 512:
        raise RetrievalError("invalid_query", "Questions must not exceed 512 tokens.")
    try:
        run_ids = sorted({UUID(str(value)) for value in run_ids}, key=str)
    except (ValueError, TypeError):
        raise RetrievalError("invalid_sources", "Provide explicit embedding run UUIDs.") from None
    if not run_ids or len(run_ids) > 100:
        raise RetrievalError("invalid_sources", "Select between 1 and 100 embedding runs.")
    if type(as_of) is not date or mode not in {"keyword", "vector", "hybrid"}:
        raise RetrievalError("invalid_query", "Choose a search mode and an explicit calendar date.")
    if mode != "keyword" and not allow_api:
        raise RetrievalError(
            "api_permission", "Vector/hybrid search requires --allow-api and may incur API usage."
        )
    timings = dict(
        embedding_seconds=0.0,
        keyword_seconds=0.0,
        vector_seconds=0.0,
        context_seconds=0.0,
        total_seconds=0.0,
    )
    with snapshot(engine) as connection:
        rows, profile = _sources(connection, run_ids, as_of)
    applicable = any(row["applicable"] for row in rows)
    query_vector, degraded, warnings, usage = None, False, [], 0
    warnings.extend("source_" + warning for row in rows for warning in row["warnings"])
    if mode != "keyword" and applicable:
        try:
            configured = EmbeddingProfile.from_env()
        except ValueError:
            raise RetrievalError(
                "configuration", "The embedding provider configuration is invalid."
            ) from None
        if profile.key != configured.key:
            raise RetrievalError(
                "profile_mismatch",
                "Configure the same embedding profile used by the selected runs.",
            )
        provider = embedder if embedder is not None else Embedder(profile)
        before = time.perf_counter()
        try:
            vectors, usage = provider.embed([query])
            if len(vectors) != 1:
                raise EmbeddingError("invalid_vectors", "Expected one query embedding.")
            query_vector = validate_vector(vectors[0])
        except EmbeddingError as error:
            if mode != "hybrid" or error.code not in {"provider_error", "invalid_vectors"}:
                raise
            degraded = True
            warnings.append("embedding_unavailable_keyword_only")
        finally:
            timings["embedding_seconds"] = time.perf_counter() - before
    # Revalidate all selected runs after the API call, in the same read-only snapshot
    # as both retrieval paths, references and parent reads. No deleted-source fallback.
    with snapshot(engine) as connection:
        rows, final_profile = _sources(connection, run_ids, as_of)
        if final_profile.key != profile.key:
            raise RetrievalError("profile_mismatch", "Selected run identity changed during search.")
        parameters = dict(run_ids=run_ids, as_of=as_of, query=query)
        keyword, vector = [], []
        if mode in {"keyword", "hybrid"}:
            before = time.perf_counter()
            keyword = [
                dict(r) for r in connection.execute(text(KEYWORD_SQL), parameters).mappings()
            ]
            timings["keyword_seconds"] = time.perf_counter() - before
        if query_vector is not None:
            before = time.perf_counter()
            vector = [
                dict(r)
                for r in connection.execute(
                    text(VECTOR_SQL), dict(parameters, query_vector=json.dumps(query_vector))
                ).mappings()
            ]
            timings["vector_seconds"] = time.perf_counter() - before
        chosen = fuse(keyword, vector)[:RESULTS]
        before = time.perf_counter()
        references = {}
        if chosen:
            refs = connection.execute(
                text(REFERENCES_SQL), dict(parameters, hashes=[r["text_sha256"] for r in chosen])
            ).mappings()
            for ref in refs:
                references.setdefault(ref["text_sha256"], []).append(dict(ref))
        results = []
        for candidate in chosen:
            refs = references[candidate["text_sha256"]]
            ref = refs[0]
            chunk = _chunk(connection, ref["run_id"], ref["chunk_id"])
            provenance = chunk["provenance"]
            # Resolve only the selected headings rather than materializing a run's registry.
            heading_path = connection.scalar(
                text("""
                SELECT coalesce(jsonb_agg(h->>'text' ORDER BY ord), '[]'::jsonb)
                FROM embedding_runs r, jsonb_array_elements(r.headings) WITH ORDINALITY AS e(h,ord)
                WHERE r.id = :run_id AND h->>'id' = ANY(:heading_ids)
                """),
                dict(
                    run_id=ref["run_id"],
                    heading_ids=[str(v) for v in provenance.get("heading_ids", [])],
                ),
            )
            result = dict(
                candidate,
                **{
                    k: v
                    for k, v in ref.items()
                    if k not in {"text_sha256", "source_rank", "source_spans"}
                },
                heading_path=heading_path,
                source_spans=provenance["source_spans"],
                text=chunk["text"],
                prefix=provenance.get("prefix", ""),
                other_sources=[
                    {
                        k: v
                        for k, v in r.items()
                        if k not in {"text_sha256", "source_rank", "total_sources"}
                    }
                    for r in refs[1:]
                ],
            )
            results.append(result)
        # Serialize IDs/dates only at the boundary, retaining raw text/Unicode exactly.
        results = json.loads(json.dumps(results, default=str))
        evidence, count, context_warnings = pack_evidence(connection, results, tokenizer)
        warnings.extend(context_warnings)
        source_runs = [
            dict(
                run_id=str(r["run_id"]),
                document_id=str(r["document_id"]),
                revision=r["revision"],
                title=r["title"],
                applicable=r["applicable"],
                sha256=r["sha256"],
                profile_hash=r["profile_hash"],
                warnings=r["warnings"],
            )
            for r in rows
        ]
        timings["context_seconds"] = time.perf_counter() - before
    timings["total_seconds"] = time.perf_counter() - started
    return dict(
        version=VERSION,
        mode=mode,
        as_of=as_of.isoformat(),
        query_tokens=query_tokens,
        degraded=degraded,
        warnings=sorted(set(warnings)),
        results=results,
        evidence=evidence,
        evidence_tokens=count,
        source_runs=source_runs,
        candidates=dict(keyword=keyword, vector=vector),
        reported_tokens=usage,
        timings=timings,
    )
