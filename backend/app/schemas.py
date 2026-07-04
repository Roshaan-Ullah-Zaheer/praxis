"""Pydantic models for the public API surface."""

from __future__ import annotations

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    filename: str
    mime: str
    size: int
    page_count: int
    status: str
    roles: list[str]
    summary: str
    chunk_count: int
    created_at: str


class UploadAccepted(BaseModel):
    id: str
    filename: str
    status: str


class RetrievedChunkOut(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page: int
    kind: str
    content: str
    score: float
