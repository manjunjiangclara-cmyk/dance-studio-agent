"""Owner-managed studio reference documents, not yet used by the agent."""

import base64
import binascii
from datetime import datetime
from pathlib import PurePosixPath
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select

from studio_copilot.api.common import Db
from studio_copilot.persistence.models import Document

router = APIRouter(prefix="/documents", tags=["Documents"])
MAX_BYTES = 1_000_000


class DocumentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    filename: str = Field(min_length=1, max_length=255)
    content_base64: str = Field(max_length=4 * ((MAX_BYTES + 2) // 3))

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be blank.")
        return value

    @field_validator("filename")
    @classmethod
    def valid_filename(cls, value):
        if (
            value != PurePosixPath(value).name
            or "\\" in value
            or not value.lower().endswith((".txt", ".md"))
            or "\x00" in value
        ):
            raise ValueError("Use a .txt or .md filename without a path.")
        return value

    @field_validator("content_base64")
    @classmethod
    def valid_content(cls, value):
        try:
            raw = base64.b64decode(value, validate=True)
            content = raw.decode("utf-8")
            if len(raw) > MAX_BYTES or "\x00" in content:
                raise ValueError("Invalid document content.")
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


class DocumentDetail(DocumentSummary):
    content: str


def find(db: Db, document_id: UUID) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(404, "Document not found.")
    return document


@router.get("", response_model=list[DocumentSummary])
def list_documents(db: Db):
    return db.scalars(select(Document).order_by(Document.updated_at.desc(), Document.id)).all()


@router.post("", response_model=DocumentDetail, status_code=201)
def create_document(body: DocumentInput, db: Db):
    document = Document(title=body.title, filename=body.filename, content=body.content())
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("/{document_id}", response_model=DocumentDetail)
def read_document(document_id: UUID, db: Db):
    return find(db, document_id)


@router.put("/{document_id}", response_model=DocumentDetail)
def update_document(document_id: UUID, body: DocumentInput, db: Db):
    document = find(db, document_id)
    document.title, document.filename, document.content = body.title, body.filename, body.content()
    db.commit()
    db.refresh(document)
    return document


@router.delete("/{document_id}")
def delete_document(document_id: UUID, db: Db):
    db.delete(find(db, document_id))
    db.commit()
    return {"deleted": True}
