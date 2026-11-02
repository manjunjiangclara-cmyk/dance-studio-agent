"""Owner-managed, revisioned source documents. Not used by the agent."""

import base64
import binascii
import hashlib
from datetime import date, datetime
from pathlib import PurePosixPath
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from sqlalchemy import func, select
from starlette.concurrency import run_in_threadpool

from studio_copilot.administration.service import AdministrationError
from studio_copilot.api.common import Db
from studio_copilot.documents.ingestion import INLINE_BYTES, receive_upload, validate_text
from studio_copilot.persistence.models import Document, DocumentRevision

router = APIRouter(prefix="/documents", tags=["Documents"])
MAX_BYTES = INLINE_BYTES  # Legacy base64 contract.


class MetadataInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    effective_from: date | None = None
    effective_to: date | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value):
        value = value.strip()
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError("Title cannot be blank or contain control characters.")
        return value

    @model_validator(mode="after")
    def dates_ordered(self):
        if self.effective_from and self.effective_to and self.effective_from > self.effective_to:
            raise ValueError("Effective from must not be after effective to.")
        return self


class FileMetadata(MetadataInput):
    filename: str = Field(min_length=1, max_length=255)

    @field_validator("filename")
    @classmethod
    def valid_filename(cls, value):
        if (
            value != PurePosixPath(value).name
            or "\\" in value
            or not value.lower().endswith((".txt", ".md"))
            or any(ord(char) < 32 for char in value)
        ):
            raise ValueError("Use a .txt or .md filename without a path or control characters.")
        return value


class MetadataUpdate(MetadataInput):
    expected_revision: int = Field(ge=1)


class TextInput(FileMetadata):
    expected_revision: int = Field(ge=1)
    content: str = Field(max_length=MAX_BYTES)

    @field_validator("content")
    @classmethod
    def valid_content(cls, value):
        validate_text(value)
        try:
            size = len(value.encode("utf-8"))
        except UnicodeEncodeError as error:
            raise ValueError("Document must be valid UTF-8 text.") from error
        if size > MAX_BYTES:
            raise ValueError("Inline editing is limited to 1 MB; replace the file instead.")
        return value


class DocumentInput(FileMetadata):
    content_base64: str = Field(max_length=4 * ((MAX_BYTES + 2) // 3))
    expected_revision: int | None = Field(default=None, ge=1)

    @field_validator("content_base64")
    @classmethod
    def valid_content(cls, value):
        try:
            raw = base64.b64decode(value, validate=True)
            content = raw.decode("utf-8")
            if len(raw) > MAX_BYTES:
                raise ValueError("Invalid document content.")
            validate_text(content)
        except (binascii.Error, UnicodeDecodeError) as error:
            raise ValueError("Document must be valid UTF-8 text.") from error
        return value

    def content(self):
        return base64.b64decode(self.content_base64).decode("utf-8")


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    filename: str
    created_at: datetime
    updated_at: datetime
    current_revision: int
    byte_size: int
    sha256: str
    hash_origin: str
    ingestion_status: str
    effective_from: date | None
    effective_to: date | None


class DocumentDetail(DocumentSummary):
    content: str


def find(db, document_id, *, lock=False):
    statement = select(Document).where(Document.id == document_id)
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    document = db.scalar(statement)
    if document is None:
        raise HTTPException(404, "Document not found.")
    return document


def revision_for(db, document, revision=None):
    result = db.scalar(
        select(DocumentRevision).where(
            DocumentRevision.document_id == document.id,
            DocumentRevision.revision
            == (document.current_revision if revision is None else revision),
        )
    )
    if result is None:
        raise HTTPException(404, "Document revision not found.")
    return result


def summary(document, revision):
    return {
        **{
            key: getattr(document, key)
            for key in ("id", "created_at", "updated_at", "current_revision")
        },
        **{
            key: getattr(revision, key)
            for key in (
                "title",
                "filename",
                "byte_size",
                "sha256",
                "hash_origin",
                "ingestion_status",
                "effective_from",
                "effective_to",
            )
        },
    }


def metadata(db, document):
    revision = revision_for(db, document)
    duplicates = db.execute(
        select(Document.id, Document.title)
        .join(
            DocumentRevision,
            (DocumentRevision.document_id == Document.id)
            & (DocumentRevision.revision == Document.current_revision),
        )
        .where(DocumentRevision.sha256 == revision.sha256, Document.id != document.id)
        .order_by(Document.id)
        .limit(20)
    ).all()
    return {**summary(document, revision), "duplicates": [dict(row._mapping) for row in duplicates]}


def save_revision(
    db,
    values,
    content,
    *,
    document_id=None,
    expected_revision=None,
    hash_origin="stored_text_utf8",
    sha256=None,
    byte_size=None,
):
    # Called only after upload and validation. Lock/commit never span network reads.
    document = find(db, document_id, lock=True) if document_id else None
    if document is not None:
        if expected_revision is None:
            raise AdministrationError(
                409,
                "expected_revision_required",
                "Reload the document and supply expected_revision before saving.",
            )
        if document.current_revision != expected_revision:
            raise AdministrationError(
                409,
                "document_revision_conflict",
                "The document changed. Your edits are retained; "
                "reload its current version before saving again.",
            )
        previous = revision_for(db, document)
        if content is None:
            content, hash_origin = previous.content, previous.hash_origin
            sha256, byte_size = previous.sha256, previous.byte_size
    raw = content.encode("utf-8") if sha256 is None else None
    digest = sha256 or hashlib.sha256(raw).hexdigest()
    size = byte_size if byte_size is not None else len(raw)
    if document is not None and all(
        getattr(previous, key) == value
        for key, value in {
            **values,
            "sha256": digest,
        }.items()
    ):
        response = metadata(db, document)
        db.commit()  # Release the lock even on a no-op.
        return response
    if document is None:
        document = Document(
            title=values["title"], filename=values["filename"], content=content, current_revision=1
        )
        db.add(document)
        db.flush()
    else:
        document.current_revision += 1
        document.title, document.filename, document.content = (
            values["title"],
            values["filename"],
            content,
        )
    revision = DocumentRevision(
        document_id=document.id,
        revision=document.current_revision,
        content=content,
        byte_size=size,
        sha256=digest,
        hash_origin=hash_origin,
        ingestion_status="ready" if content.replace("\ufeff", "").strip() else "needs_correction",
        **values,
    )
    db.add(revision)
    db.flush()
    # Freeze primitive response values while this request still owns the document
    # lock. After commit a competing writer may advance the mutable pointer.
    response = metadata(db, document)
    db.commit()
    return response


@router.get("", response_model=list[DocumentSummary])
def list_documents(db: Db):
    rows = db.execute(
        select(Document, DocumentRevision)
        .join(
            DocumentRevision,
            (DocumentRevision.document_id == Document.id)
            & (DocumentRevision.revision == Document.current_revision),
        )
        .order_by(Document.updated_at.desc(), Document.id)
    )
    return [summary(document, revision) for document, revision in rows]


@router.post("/upload", status_code=201)
async def upload_document(request: Request, db: Db):
    return await upload(request, db)


@router.put("/{document_id}/upload")
async def replace_document(document_id: UUID, request: Request, db: Db):
    return await upload(request, db, document_id)


async def upload(request, db, document_id=None):
    source = await receive_upload(request)
    try:
        fields = {key: value or None for key, value in source.fields.items()}
        expected = fields.pop("expected_revision", None)
        if document_id is not None and (
            expected is None
            or not str(expected).isascii()
            or not str(expected).isdigit()
            or int(expected) < 1
        ):
            raise AdministrationError(
                422, "invalid_document", "Replacement requires expected_revision."
            )
        if document_id is None and expected is not None:
            raise AdministrationError(
                422, "invalid_document", "New documents cannot specify expected_revision."
            )
        values = FileMetadata.model_validate({**fields, "filename": source.filename}).model_dump()
    except ValidationError as error:
        raise AdministrationError(
            422, "invalid_document", "Check the document title, filename and effective dates."
        ) from error
    return await run_in_threadpool(
        save_revision,
        db,
        values,
        source.content,
        document_id=document_id,
        expected_revision=int(expected) if expected else None,
        hash_origin="upload_bytes",
        sha256=source.sha256,
        byte_size=source.byte_size,
    )


@router.post("", response_model=DocumentDetail, status_code=201)
def create_document(body: DocumentInput, db: Db):
    result = save_revision(
        db, body.model_dump(include=set(FileMetadata.model_fields)), body.content()
    )
    return {**result, "content": body.content()}


@router.get("/{document_id}/metadata")
def read_metadata(document_id: UUID, db: Db):
    return metadata(db, find(db, document_id))


@router.patch("/{document_id}/metadata")
def update_metadata(document_id: UUID, body: MetadataUpdate, db: Db):
    document = find(db, document_id, lock=True)
    previous = revision_for(db, document)
    values = {
        "title": previous.title,
        "filename": previous.filename,
        "effective_from": previous.effective_from,
        "effective_to": previous.effective_to,
    }
    values.update(body.model_dump(exclude={"expected_revision"}, exclude_unset=True))
    try:
        FileMetadata.model_validate(values)  # Validate dates after merging omitted fields.
    except ValidationError as error:
        raise AdministrationError(
            422, "invalid_document", "Check the document title and effective dates."
        ) from error
    return save_revision(
        db, values, None, document_id=document_id, expected_revision=body.expected_revision
    )


@router.put("/{document_id}/text")
def update_text(document_id: UUID, body: TextInput, db: Db):
    document = find(db, document_id)
    if revision_for(db, document).byte_size > MAX_BYTES:
        raise AdministrationError(
            409,
            "document_preview_required",
            "Replace this file to edit a document larger than 1 MB.",
        )
    return save_revision(
        db,
        body.model_dump(include=set(FileMetadata.model_fields)),
        body.content,
        document_id=document_id,
        expected_revision=body.expected_revision,
    )


@router.get("/{document_id}/revisions")
def list_revisions(document_id: UUID, db: Db):
    document = find(db, document_id)
    revisions = db.scalars(
        select(DocumentRevision)
        .where(DocumentRevision.document_id == document_id)
        .order_by(DocumentRevision.revision.desc())
    )
    return [
        {
            **summary(document, revision),
            "revision": revision.revision,
            "created_at": revision.created_at,
        }
        for revision in revisions
    ]


@router.get("/{document_id}/revisions/{revision}/preview")
def preview(
    document_id: UUID,
    revision: int,
    db: Db,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20_000, ge=1, le=20_000),
):
    document = find(db, document_id)
    snapshot = revision_for(db, document, revision)
    # PostgreSQL substring/length count Unicode characters and avoid transferring full sources.
    total, content = db.execute(
        select(
            func.length(DocumentRevision.content),
            func.substr(DocumentRevision.content, offset + 1, limit),
        ).where(DocumentRevision.id == snapshot.id)
    ).one()
    if offset > total:
        raise HTTPException(422, "Preview offset is past the end of the document.")
    end = offset + len(content)
    # Prefer a complete line where possible, without stalling on a very long line.
    if end < total and "\n" in content:
        content = content[: content.rfind("\n") + 1]
        end = offset + len(content)
    return {
        "revision": revision,
        "content": content,
        "total_characters": total,
        "next_offset": end if end < total else None,
        "offset": offset,
    }


@router.get("/{document_id}", response_model=DocumentDetail)
def read_document(document_id: UUID, db: Db):
    document = find(db, document_id)
    snapshot = revision_for(db, document)
    if snapshot.byte_size > MAX_BYTES:
        raise AdministrationError(
            409,
            "document_preview_required",
            "Use the revision preview for documents larger than 1 MB.",
        )
    return {**summary(document, snapshot), "content": snapshot.content}


@router.put("/{document_id}", response_model=DocumentDetail)
def update_document(document_id: UUID, body: DocumentInput, db: Db):
    result = save_revision(
        db,
        body.model_dump(include=set(FileMetadata.model_fields)),
        body.content(),
        document_id=document_id,
        expected_revision=body.expected_revision,
    )
    return {**result, "content": body.content()}


@router.delete("/{document_id}")
def delete_document(document_id: UUID, db: Db):
    document = find(db, document_id, lock=True)
    # Explicit deletion also keeps SQLite-based API tests consistent with PostgreSQL cascades.
    from sqlalchemy import delete

    db.execute(delete(DocumentRevision).where(DocumentRevision.document_id == document_id))
    db.delete(document)
    db.commit()
    return {"deleted": True}
