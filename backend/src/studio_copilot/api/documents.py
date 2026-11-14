"""Owner-managed, revisioned documents and explicit answer activation."""

import base64
import binascii
import hashlib
from datetime import UTC, date, datetime
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from sqlalchemy import func, select
from starlette.concurrency import run_in_threadpool

from studio_copilot.administration.service import AdministrationError
from studio_copilot.api.common import Db
from studio_copilot.documents import activation
from studio_copilot.documents.ingestion import INLINE_BYTES, receive_upload, validate_text
from studio_copilot.persistence.models import Document, DocumentActivation, DocumentRevision

router = APIRouter(prefix="/documents", tags=["Documents"])
MAX_BYTES = INLINE_BYTES  # Legacy base64 contract.


@router.get("/{document_id}/answer-activation")
def answer_activation(document_id: UUID, db: Db):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(404, "Document not found.")
    if document.archived_at is not None:
        return {"status": "disabled", "error": None}
    row = db.get(DocumentActivation, document_id)
    if row and row.status == "enabled" and row.revision != document.current_revision:
        return {
            "status": "failed",
            "error": "The document changed. Prepare its current revision again.",
        }
    return activation.view(row)


@router.post("/{document_id}/answer-activation")
def enable_answers(document_id: UUID, background: BackgroundTasks, request: Request, db: Db):
    try:
        activation.check_setup()
    except Exception:
        raise HTTPException(503, activation.SETUP_ERROR) from None
    document = find(db, document_id, lock=True)
    row = db.get(DocumentActivation, document_id, with_for_update=True)
    if document is None:
        raise HTTPException(404, "Document not found.")
    require_editable(document)
    if row is None:
        # The document lock serializes concurrent creation of the first activation.
        row = db.get(DocumentActivation, document_id, with_for_update=True)
    if (
        row
        and row.revision == document.current_revision
        and activation.view(row)["status"] in {"preparing", "enabled"}
    ):
        return activation.view(row)
    if row is None:
        row = DocumentActivation(
            document_id=document_id, revision=document.current_revision, status="disabled"
        )
        db.add(row)
    token = uuid4()
    row.revision, row.status, row.run_id = document.current_revision, "preparing", None
    row.token, row.lease_expires_at, row.error = token, datetime.now(UTC) + activation.LEASE, None
    revision = row.revision
    db.commit()
    background.add_task(activation.worker, request.app.state.engine, document_id, revision, token)
    return {"status": "preparing", "error": None}


@router.delete("/{document_id}/answer-activation")
def disable_answers(document_id: UUID, db: Db):
    document = find(db, document_id, lock=True)
    row = db.get(DocumentActivation, document_id, with_for_update=True)
    if document is None:
        raise HTTPException(404, "Document not found.")
    if row is not None:
        row.status, row.run_id, row.token, row.lease_expires_at, row.error = (
            "disabled",
            None,
            None,
            None,
            None,
        )
        db.commit()
    return {"status": "disabled", "error": None}


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
    archived_at: datetime | None
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


def require_editable(document):
    if document.archived_at is not None:
        raise AdministrationError(409, "document_archived", "Archived documents are read-only.")


def prepare_revision(db, document, background, engine):
    """Register the replacement claim while holding the source document lock."""
    row = db.get(DocumentActivation, document.id, with_for_update=True)
    if row is None:
        row = DocumentActivation(document_id=document.id)
        db.add(row)
    row.revision, row.run_id = document.current_revision, None
    row.token, row.lease_expires_at, row.error = None, None, None
    try:
        activation.check_setup()
    except Exception:
        row.status, row.error = "failed", activation.SETUP_ERROR
        return
    token = uuid4()
    row.status, row.token = "preparing", token
    row.lease_expires_at = datetime.now(UTC) + activation.LEASE
    background.add_task(activation.worker, engine, document.id, document.current_revision, token)


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
            for key in ("id", "created_at", "updated_at", "current_revision", "archived_at")
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
        .where(
            DocumentRevision.sha256 == revision.sha256,
            Document.id != document.id,
            Document.archived_at.is_(None),
        )
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
    background=None,
    engine=None,
):
    # Called only after upload and validation. Lock/commit never span network reads.
    document = find(db, document_id, lock=True) if document_id else None
    if document is not None:
        require_editable(document)
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
    if document_id is not None:
        prepare_revision(db, document, background, engine)
    db.flush()
    # Freeze primitive response values while this request still owns the document
    # lock. After commit a competing writer may advance the mutable pointer.
    response = metadata(db, document)
    db.commit()
    return response


@router.get("", response_model=list[DocumentSummary])
def list_documents(db: Db, archived: bool = False):
    rows = db.execute(
        select(Document, DocumentRevision)
        .join(
            DocumentRevision,
            (DocumentRevision.document_id == Document.id)
            & (DocumentRevision.revision == Document.current_revision),
        )
        .where(Document.archived_at.is_not(None) if archived else Document.archived_at.is_(None))
        .order_by(Document.updated_at.desc(), Document.id)
    )
    return [summary(document, revision) for document, revision in rows]


@router.post("/upload", status_code=201)
async def upload_document(request: Request, background: BackgroundTasks, db: Db):
    return await upload(request, db, background=background)


@router.put("/{document_id}/upload")
async def replace_document(
    document_id: UUID, request: Request, background: BackgroundTasks, db: Db
):
    return await upload(request, db, document_id, background=background)


async def upload(request, db, document_id=None, *, background=None):
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
        background=background,
        engine=request.app.state.engine,
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
def update_metadata(
    document_id: UUID, body: MetadataUpdate, request: Request, background: BackgroundTasks, db: Db
):
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
        db,
        values,
        None,
        document_id=document_id,
        expected_revision=body.expected_revision,
        background=background,
        engine=request.app.state.engine,
    )


@router.put("/{document_id}/text")
def update_text(
    document_id: UUID, body: TextInput, request: Request, background: BackgroundTasks, db: Db
):
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
        background=background,
        engine=request.app.state.engine,
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
def update_document(
    document_id: UUID, body: DocumentInput, request: Request, background: BackgroundTasks, db: Db
):
    result = save_revision(
        db,
        body.model_dump(include=set(FileMetadata.model_fields)),
        body.content(),
        document_id=document_id,
        expected_revision=body.expected_revision,
        background=background,
        engine=request.app.state.engine,
    )
    return {**result, "content": body.content()}


class ArchiveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)


def archive(db, document_id, expected_revision=None):
    document = find(db, document_id, lock=True)
    if expected_revision is not None and document.current_revision != expected_revision:
        raise AdministrationError(
            409, "document_revision_conflict", "Reload the current revision before archiving."
        )
    if document.archived_at is None:
        document.archived_at = datetime.now(UTC)
    row = db.get(DocumentActivation, document_id, with_for_update=True)
    if row is not None:
        row.status, row.run_id, row.token, row.lease_expires_at, row.error = (
            "disabled",
            None,
            None,
            None,
            None,
        )
    db.flush()
    response = metadata(db, document)
    db.commit()
    return response


@router.post("/{document_id}/archive")
def archive_document(document_id: UUID, body: ArchiveInput, db: Db):
    return archive(db, document_id, body.expected_revision)


@router.delete("/{document_id}")
def delete_document(document_id: UUID, db: Db):
    archive(db, document_id)
    return {"deleted": True}
