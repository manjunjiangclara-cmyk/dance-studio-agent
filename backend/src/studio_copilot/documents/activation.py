"""Explicit, revision-pinned publication for document answers."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.embedding.pipeline import run
from studio_copilot.documents.embedding.provider import EmbeddingProfile
from studio_copilot.documents.operations import task
from studio_copilot.documents.reranking.runtime import verify_model
from studio_copilot.persistence.models import Document, DocumentActivation, EmbeddingRun

LEASE = timedelta(minutes=30)
SETUP_ERROR = (
    "Document answers need server configuration and prepared tokenizer and reranker assets. "
    "Contact the administrator."
)
PROCESS_ERROR = "Preparation failed or was interrupted. Check server configuration and try again."


def check_setup():
    if os.environ.get("STUDIO_DOCUMENT_ANSWERS", "false").lower() != "true":
        raise ValueError(SETUP_ERROR)
    if not all(
        os.environ.get(k)
        for k in (
            "OPENAI_API_KEY",
            "OPENAI_MODEL",
            "STUDIO_TOKENIZER_CACHE",
            "STUDIO_RERANKER_CACHE",
        )
    ):
        raise ValueError(SETUP_ERROR)
    EmbeddingProfile.from_env()
    tokenizer = Path(os.environ["STUDIO_TOKENIZER_CACHE"])
    if not (tokenizer / "cl100k_base.tiktoken").is_file():
        raise ValueError(SETUP_ERROR)
    verify_model(Path(os.environ["STUDIO_RERANKER_CACHE"]), "cross-encoder/ms-marco-MiniLM-L6-v2")


def view(row):
    if row is None:
        return {"status": "disabled", "error": None}
    if row.status == "preparing" and (
        row.lease_expires_at is None or row.lease_expires_at <= datetime.now(UTC)
    ):
        return {"status": "failed", "error": PROCESS_ERROR}
    return {"status": row.status, "error": row.error}


def worker(engine, document_id, revision, token):
    """A fenced worker; only the current request may publish its completed run."""

    def progress(_value):
        with Session(engine) as db, db.begin():
            row = db.get(DocumentActivation, document_id, with_for_update=True)
            if row is not None and row.token == token and row.status == "preparing":
                row.lease_expires_at = datetime.now(UTC) + LEASE

    try:
        with task():
            result = run(
                engine,
                document_id,
                revision,
                Tokenizer(Path(os.environ["STUDIO_TOKENIZER_CACHE"])),
                EmbeddingProfile.from_env(),
                progress=progress,
            )
        run_id = UUID(result["run_id"])
        if result["status"] != "complete" or not result["prepared"]:
            raise ValueError("Preparation did not complete")
        check_setup()
        with Session(engine) as db, db.begin():
            db.execute(text("SELECT pg_advisory_xact_lock(582910742)"))
            row = db.get(DocumentActivation, document_id, with_for_update=True)
            if row is None or row.token != token or row.status != "preparing":
                return
            document = db.get(Document, document_id, with_for_update=True)
            prepared = db.get(EmbeddingRun, run_id)
            enabled = db.execute(
                select(DocumentActivation, EmbeddingRun)
                .join(Document, Document.id == DocumentActivation.document_id)
                .outerjoin(EmbeddingRun, EmbeddingRun.id == DocumentActivation.run_id)
                .where(
                    DocumentActivation.status == "enabled",
                    DocumentActivation.revision == Document.current_revision,
                )
            ).all()
            if (
                document is None
                or document.current_revision != revision
                or prepared is None
                or prepared.document_id != document_id
                or prepared.revision != revision
                or prepared.status != "complete"
                or not prepared.prepared
                or prepared.profile_hash != EmbeddingProfile.from_env().key
                or len(enabled) >= 100
                or any(
                    other is None or other.profile_hash != prepared.profile_hash
                    for _, other in enabled
                )
            ):
                raise ValueError("Source changed or activation limit reached")
            row.status, row.run_id, row.token, row.lease_expires_at, row.error = (
                "enabled",
                run_id,
                None,
                None,
                None,
            )
    except Exception:
        with Session(engine) as db, db.begin():
            row = db.get(DocumentActivation, document_id, with_for_update=True)
            if row is not None and row.token == token and row.status == "preparing":
                row.status, row.token, row.lease_expires_at, row.error = (
                    "failed",
                    None,
                    None,
                    PROCESS_ERROR,
                )
