"""Documents API: upload (multimodal ingest), list, detail, delete, role tagging."""

from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Body, File, Form, HTTPException, Response, UploadFile

from .. import config
from ..billing import tiers
from ..ingest.pipeline import ingest_path
from ..schemas import DocumentOut, UploadAccepted
from ..store import get_store
from ..store.base import DocumentRecord

router = APIRouter(prefix="/documents", tags=["documents"])


def _to_out(doc: DocumentRecord) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        filename=doc.filename,
        mime=doc.mime,
        size=doc.size,
        page_count=doc.page_count,
        status=doc.status,
        roles=doc.roles,
        summary=doc.summary,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at,
    )


@router.post("", response_model=UploadAccepted, status_code=202)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    roles: str = Form("public"),
) -> UploadAccepted:
    store = get_store()

    # Tier gating — a no-op unless billing is configured (demo stays unlimited).
    allowed, message = tiers.check_can_upload(store, config.DEFAULT_OWNER)
    if not allowed:
        raise HTTPException(402, message)

    role_list = [r.strip() for r in roles.split(",") if r.strip()] or ["public"]

    safe_name = os.path.basename(file.filename or "document")
    dest = os.path.join(store.data_dir, "files", f"{uuid.uuid4().hex}_{safe_name}")  # type: ignore[attr-defined]
    data = await file.read()
    with open(dest, "wb") as fh:
        fh.write(data)

    # Pre-register so the client can poll status immediately; ingest in background.
    from ..ingest.pipeline import file_hash, _guess_mime

    digest = file_hash(data)
    existing = store.find_document_by_hash(config.DEFAULT_OWNER, digest)
    if existing and existing.status == "ready":
        return UploadAccepted(id=existing.id, filename=existing.filename, status=existing.status)

    doc_id = store.create_document(
        config.DEFAULT_OWNER, safe_name, _guess_mime(safe_name), len(data), digest, dest, "queued"
    )
    store.set_document_roles(doc_id, role_list)
    background.add_task(_run_ingest, dest, safe_name, role_list)
    return UploadAccepted(id=doc_id, filename=safe_name, status="queued")


def _run_ingest(dest: str, name: str, roles: list[str]) -> None:
    ingest_path(get_store(), config.DEFAULT_OWNER, dest, name, roles)


@router.get("", response_model=list[DocumentOut])
def list_documents() -> list[DocumentOut]:
    return [_to_out(d) for d in get_store().list_documents(config.DEFAULT_OWNER)]


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str) -> DocumentOut:
    doc = get_store().get_document(doc_id)
    if not doc:
        raise HTTPException(404, "document not found")
    return _to_out(doc)


@router.post("/{doc_id}/roles", response_model=DocumentOut)
def set_roles(doc_id: str, roles: list[str] = Body(..., embed=True)) -> DocumentOut:
    store = get_store()
    if not store.get_document(doc_id):
        raise HTTPException(404, "document not found")
    store.set_document_roles(doc_id, roles or ["public"])
    return _to_out(store.get_document(doc_id))  # type: ignore[arg-type]


@router.delete("/{doc_id}")
def delete_document(doc_id: str) -> Response:
    get_store().delete_document(doc_id)
    return Response(status_code=204)
