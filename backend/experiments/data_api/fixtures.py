"""Small fictional corpus with fixed vectors; no embedding/model provider calls."""

import hashlib
import json
from dataclasses import asdict
from datetime import date
from uuid import UUID

from studio_copilot.documents.embedding.provider import EmbeddingProfile

from .sql import identifier

AS_OF = date(2027, 2, 8)
TEXTS = (
    "Cancellations need 24 hours notice. Café 💃.",
    "Clean ballet shoes are required.",
    "Cancellations need a teacher review.",
)


def vector(index=0):
    result = [0.0] * 1536
    result[index] = 1.0
    return result


class FixtureVectors:
    calls = 0

    def embed(self, texts):
        self.calls += 1
        return [vector() for _ in texts], 0


class FixtureTokenizer:
    """Deterministic word counter: transport parity only, not tokenizer-quality evidence."""

    def count(self, text):
        return len(text.split())


def corpus(sql, schema):
    schema = identifier(schema)
    definitions = {
        "documents": "id uuid PRIMARY KEY, archived_at timestamptz",
        "document_revisions": """document_id uuid, revision integer, title text, sha256 text,
            ingestion_status text, effective_from date, effective_to date,
            PRIMARY KEY(document_id,revision)""",
        "embedding_runs": """id uuid PRIMARY KEY, document_id uuid, revision integer,
            status text, prepared boolean, profile_hash text, profile jsonb, warnings jsonb,
            headings jsonb""",
        "embedding_vectors": "key text PRIMARY KEY, embedding public.vector(1536)",
        "document_chunks": """run_id uuid, chunk_id text, parent_id text, kind text,
            text text, text_sha256 text, vector_key text, ordinal integer, provenance jsonb,
            PRIMARY KEY(run_id,chunk_id)""",
    }
    for table, fields in definitions.items():
        sql.query(f"CREATE TABLE {schema}.{table} ({fields})")
    profile = EmbeddingProfile()
    runs = []
    for index in range(4):
        document, run_id = UUID(int=index + 1), UUID(int=index + 11)
        text = TEXTS[index % 3]
        sha = hashlib.sha256(text.encode()).hexdigest()
        # Fourth source duplicates the first passage, with its own source reference.
        runs.append(run_id)
        sql.query(f"INSERT INTO {schema}.documents VALUES (:id,NULL)", {"id": document})
        sql.query(
            f"""INSERT INTO {schema}.document_revisions VALUES
            (:document,1,:title,:sha,'ready',CAST(:start AS date),CAST(:end AS date))""",
            dict(
                document=document,
                title=f"Fictional handbook {index}",
                sha=sha,
                start="2027-02-08",
                end="2027-02-28",
            ),
        )
        sql.query(
            f"""INSERT INTO {schema}.embedding_runs VALUES
            (:id,:document,1,'complete',true,:hash,CAST(:profile AS jsonb),'[]','[]')""",
            dict(id=run_id, document=document, hash=profile.key, profile=asdict(profile)),
        )
        sql.query(
            f"""INSERT INTO {schema}.embedding_vectors VALUES
            (:key,CAST(:vector AS public.vector)) ON CONFLICT DO NOTHING""",
            dict(key=sha, vector=json.dumps(vector(1 if index == 1 else 0))),
        )
        spans = [dict(start=0, end=len(text))]
        for kind in ("parent", "passage"):
            sql.query(
                f"""INSERT INTO {schema}.document_chunks VALUES
                (:run,:chunk,:parent,:kind,:text,:sha,:key,0,CAST(:provenance AS jsonb))""",
                dict(
                    run=run_id,
                    chunk=kind,
                    parent="parent" if kind == "passage" else None,
                    kind=kind,
                    text=text,
                    sha=sha,
                    key=sha if kind == "passage" else None,
                    provenance={"source_spans": spans, "prefix": "", "heading_ids": []},
                ),
            )
    return runs


def retrieve(engine, runs, *, query="cancellation", as_of=AS_OF):
    from studio_copilot.documents.retrieval.engine import search

    return search(
        engine, runs, query, as_of, FixtureTokenizer(), allow_api=True, embedder=FixtureVectors()
    )


def stable(result):
    """Drop only timing/operational accounting, retaining scores and exact evidence."""
    return {k: v for k, v in result.items() if k not in {"timings", "operations"}}
