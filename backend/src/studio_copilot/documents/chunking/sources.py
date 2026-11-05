"""Materialize one validated immutable source, then release the read transaction."""

import hashlib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from uuid import UUID

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from studio_copilot.documents.ingestion import MAX_BYTES
from studio_copilot.persistence.models import DocumentRevision


@dataclass(frozen=True)
class Source:
    text: str = field(repr=False)
    title: str
    filename: str
    sha256: str
    byte_size: int
    document_id: str | None = None
    revision: int | None = None
    hash_origin: str = "file_bytes"
    effective_from: str | None = None
    effective_to: str | None = None
    created_at: str | None = None

    def metadata(self):
        return {key: value for key, value in asdict(self).items() if key != "text"}

    def validate(self):
        if Path(self.filename).suffix.lower() not in {".md", ".txt"}:
            raise ValueError("Choose a UTF-8 .md or .txt document.")
        if not self.title.strip() or len(self.title) > 200:
            raise ValueError("The title must contain 1–200 characters.")
        raw = self.text.encode("utf-8")
        if len(raw) > MAX_BYTES:
            raise ValueError(f"Documents must be at most {MAX_BYTES:,} bytes.")
        if "\x00" in self.text or not self.text.replace("\ufeff", "").strip():
            raise ValueError("Document text cannot be blank or contain NUL; correct this revision.")
        if len(raw) != self.byte_size or hashlib.sha256(raw).hexdigest() != self.sha256:
            raise ValueError("Source bytes do not match the revision size or SHA-256.")
        return self


def load_file(path: Path, title: str | None = None) -> Source:
    # A bounded read enforces the limit even for a growing file or an incorrect stat size.
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError(f"Documents must be at most {MAX_BYTES:,} bytes.")
    return Source(
        text=raw.decode("utf-8"),
        title=title if title is not None else path.stem,
        filename=path.name,
        sha256=hashlib.sha256(raw).hexdigest(),
        byte_size=len(raw),
    ).validate()


def load_revision(engine: Engine, document_id: UUID, revision: int) -> Source:
    if revision < 1:
        raise ValueError("Specify a positive revision number.")
    # Explicit columns include the deferred content in the SAME statement as metadata.
    # No current-document lookup, lazy loads, locks or writes; concurrent deletes can
    # only yield either this complete MVCC snapshot or a clear not-found result.
    with Session(engine) as session:
        session.execute(text("SET TRANSACTION READ ONLY"))
        row = (
            session.execute(
                select(
                    DocumentRevision.content,
                    DocumentRevision.title,
                    DocumentRevision.filename,
                    DocumentRevision.sha256,
                    DocumentRevision.byte_size,
                    DocumentRevision.document_id,
                    DocumentRevision.revision,
                    DocumentRevision.hash_origin,
                    DocumentRevision.effective_from,
                    DocumentRevision.effective_to,
                    DocumentRevision.created_at,
                ).where(
                    DocumentRevision.document_id == document_id,
                    DocumentRevision.revision == revision,
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ValueError("The requested document revision does not exist or was deleted.")
        values = dict(row)
        values["text"] = values.pop("content")
        values["document_id"] = str(values["document_id"])
        for key in ("effective_from", "effective_to", "created_at"):
            if values[key] is not None:
                values[key] = values[key].isoformat()
        source = Source(**values)
    return source.validate()
