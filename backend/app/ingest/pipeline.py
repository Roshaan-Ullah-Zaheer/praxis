"""Ingestion orchestration: file → parse → tables → OCR → chunk → embed → index.

Idempotent on file content (re-uploading the same bytes reuses the prior index),
status-tracked at each stage, and resilient — a failure marks the document
``failed`` rather than crashing the request.
"""

from __future__ import annotations

import hashlib
import logging
import os

from .. import llm
from ..store.base import Store
from .chunk import chunk_pages
from .embed import embed_chunks
from .parse import parse_document
from .tables import extract_pdf_tables

logger = logging.getLogger(__name__)

_SUMMARY_SYSTEM = (
    "Summarize this document in 1-2 sentences for a retrieval index. State its document "
    "type and main subject. Be concise and factual. No preamble, no markdown."
)


def file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _guess_mime(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".txt": "text/plain",
        ".md": "text/markdown",
    }.get(ext, "application/octet-stream")


def _generate_summary(chunks) -> str:
    sample = "\n\n".join(c.content for c in chunks[:6])[:6000]
    if not sample.strip():
        return ""
    try:
        chat = llm.get_chat(temperature=0.2, max_tokens=512)
        result = chat.invoke([("system", _SUMMARY_SYSTEM), ("user", sample)])
        return (result.content or "").strip()
    except Exception as exc:  # noqa: BLE001 - summary is best-effort
        logger.warning("summary generation failed: %s", exc)
        return ""


def ingest_path(
    store: Store,
    owner_id: str,
    file_path: str,
    filename: str,
    roles: list[str] | None = None,
) -> str:
    """Ingest a file already saved on disk. Returns the document id."""
    roles = roles or ["public"]
    with open(file_path, "rb") as fh:
        data = fh.read()
    digest = file_hash(data)

    existing = store.find_document_by_hash(owner_id, digest)
    if existing and existing.status == "ready":
        logger.info("idempotent hit: %s already ingested as %s", filename, existing.id)
        return existing.id

    mime = _guess_mime(filename)
    doc_id = store.create_document(
        owner_id, filename, mime, len(data), digest, file_path, status="parsing"
    )
    store.set_document_roles(doc_id, roles)

    try:
        pages = parse_document(file_path, mime)
        tables = extract_pdf_tables(file_path) if mime == "application/pdf" else []
        chunks = chunk_pages(pages, tables)
        if not chunks:
            store.update_document_status(doc_id, "failed", page_count=len(pages))
            return doc_id

        store.update_document_status(doc_id, "embedding", page_count=len(pages))
        embed_chunks(chunks, store)
        store.add_chunks(doc_id, chunks)

        summary = _generate_summary(chunks)
        store.update_document_status(doc_id, "ready", page_count=len(pages), summary=summary)
        logger.info("ingested %s → %s (%d chunks)", filename, doc_id, len(chunks))
    except Exception as exc:  # noqa: BLE001 - surface as failed status, don't crash
        logger.exception("ingestion failed for %s: %s", filename, exc)
        store.update_document_status(doc_id, "failed")
    return doc_id
