"""Explicit preparation and isolated source selection for public demo documents."""

import hashlib
import json
import os
from dataclasses import asdict
from datetime import date
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import delete, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from studio_copilot.documents import online
from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.chunking.engine import Config, digest
from studio_copilot.documents.embedding import pipeline
from studio_copilot.documents.embedding.provider import EmbeddingProfile
from studio_copilot.persistence.database import make_engine
from studio_copilot.persistence.models import Document, DocumentActivation, DocumentRevision
from studio_copilot.public_demo.fixtures import PUBLIC_DOCUMENTS


def sources():
    result = []
    for item in PUBLIC_DOCUMENTS:
        content = item["content"]
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        key = json.dumps(
            [item["id"], item["title"], item["filename"], item["revision"], digest],
            ensure_ascii=False,
        )
        result.append((item, uuid5(NAMESPACE_URL, "studio-public-document:" + key), digest))
    if len({item[1] for item in result}) != len(result):
        raise ValueError("Duplicate public documents")
    return result


def engine_from_env():
    url = os.environ.get("STUDIO_PUBLIC_DOCUMENT_DATABASE_URL")
    owner_url = os.environ.get("DATABASE_URL")
    if not url or not owner_url:
        raise online.OnlineError("configuration")
    demo, owner = make_url(url), make_url(owner_url)
    if not demo.database or not owner.database or demo.database == owner.database:
        raise online.OnlineError("configuration")
    demo_engine = make_engine(url)
    owner_engine = make_engine(owner_url)
    try:
        statement = text("SELECT current_database(), inet_server_addr(), inet_server_port()")
        with demo_engine.connect() as demo_db, owner_engine.connect() as owner_db:
            if demo_db.execute(statement).one() == owner_db.execute(statement).one():
                raise online.OnlineError("configuration")
    except Exception:
        demo_engine.dispose()
        raise
    finally:
        owner_engine.dispose()
    return demo_engine


def prepare(engine, tokenizer, profile, *, embedder=None):
    """Prepare all immutable revisions before atomically publishing the set."""
    expected = sources()
    with Session(engine) as db, db.begin():
        for item, document_id, digest in expected:
            if db.get(Document, document_id) is None:
                db.add(
                    Document(
                        id=document_id,
                        title=item["title"],
                        filename=item["filename"],
                        content=item["content"],
                        current_revision=item["revision"],
                    )
                )
                db.flush()
                db.add(
                    DocumentRevision(
                        document_id=document_id,
                        revision=item["revision"],
                        title=item["title"],
                        filename=item["filename"],
                        content=item["content"],
                        byte_size=len(item["content"].encode()),
                        sha256=digest,
                        hash_origin="stored_text_utf8",
                        ingestion_status="ready",
                    )
                )
    prepared = []
    for item, document_id, _ in expected:
        result = pipeline.run(
            engine, document_id, item["revision"], tokenizer, profile, embedder=embedder
        )
        if result["status"] != "complete" or not result["prepared"]:
            raise online.OnlineError("source_changed")
        prepared.append((document_id, item["revision"], UUID(str(result["run_id"]))))
    with Session(engine) as db, db.begin():
        rows = online.source_rows(db, [row[2] for row in prepared], date.today())
        validate_sources(rows, expected, profile)
        db.execute(text("SELECT pg_advisory_xact_lock(582910743)"))
        db.execute(
            text(
                "CREATE TABLE IF NOT EXISTS public_demo_sources "
                "(document_id uuid PRIMARY KEY REFERENCES documents(id))"
            )
        )
        previous = db.execute(text("SELECT document_id FROM public_demo_sources")).scalars().all()
        if previous:
            db.execute(
                delete(DocumentActivation).where(DocumentActivation.document_id.in_(previous))
            )
        db.execute(text("DELETE FROM public_demo_sources"))
        db.add_all(
            DocumentActivation(document_id=doc, revision=rev, status="enabled", run_id=run)
            for doc, rev, run in prepared
        )
        db.flush()
        for doc, _, _ in prepared:
            db.execute(
                text("INSERT INTO public_demo_sources (document_id) VALUES (:id)"), {"id": doc}
            )
    return prepared


def validate_sources(rows, expected, profile):
    by_id = {document_id: (item, checksum) for item, document_id, checksum in expected}
    if len(rows) != len(by_id):
        raise online.OnlineError("source_changed")
    chunker_hash = digest(asdict(Config()))
    for run, doc, revision in rows:
        if doc.id not in by_id:
            raise online.OnlineError("source_changed")
        item, checksum = by_id[doc.id]
        if (
            revision.revision != item["revision"]
            or revision.title != item["title"]
            or revision.filename != item["filename"]
            or revision.sha256 != checksum
            or hashlib.sha256(revision.content.encode()).hexdigest() != checksum
            or run.profile_hash != profile.key
            or run.chunker_hash != chunker_hash
        ):
            raise online.OnlineError("source_changed")


def configuration(engine, *, tokenizer_cache=None, reranker_cache=None):
    try:
        with Session(engine) as db:
            ids = db.execute(text("SELECT document_id FROM public_demo_sources")).scalars().all()
            rows = db.scalars(
                select(DocumentActivation).where(
                    DocumentActivation.status == "enabled", DocumentActivation.document_id.in_(ids)
                )
            ).all()
            documents = sources()
            expected = {
                doc_id: (item["revision"], checksum) for item, doc_id, checksum in documents
            }
            if {row.document_id for row in rows} != set(expected) or any(
                row.run_id is None or row.revision != expected[row.document_id][0] for row in rows
            ):
                raise online.OnlineError("source_changed")
            runs = tuple(row.run_id for row in sorted(rows, key=lambda row: str(row.document_id)))
            selected = online.source_rows(db, runs, date.today())
            validate_sources(selected, documents, EmbeddingProfile.from_env())
        return online.Configuration(
            runs,
            Path(tokenizer_cache or os.environ["STUDIO_TOKENIZER_CACHE"]),
            Path(reranker_cache or os.environ["STUDIO_RERANKER_CACHE"]),
        )
    except online.OnlineError:
        raise
    except Exception:
        raise online.OnlineError("configuration") from None


def main():
    engine = engine_from_env()
    try:
        tokenizer = Tokenizer(Path(os.environ["STUDIO_TOKENIZER_CACHE"]))
        prepare(engine, tokenizer, EmbeddingProfile.from_env())
        configuration(engine)
        print("Public demo document index prepared.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
