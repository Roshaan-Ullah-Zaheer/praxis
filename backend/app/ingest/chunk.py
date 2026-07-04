"""Structure-aware chunking.

Text is split on paragraph boundaries into overlapping windows; extracted tables
are kept whole as their own chunks so the LLM never sees a half table.
"""

from __future__ import annotations

from .. import config
from ..store.base import ChunkRecord
from .parse import PageContent


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _split_text(text: str, size: int, overlap: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paras:
        if current and len(current) + len(para) + 2 > size:
            chunks.append(current)
            # carry an overlap tail into the next window for context continuity
            current = (current[-overlap:] + "\n\n" + para) if overlap else para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current.strip():
        chunks.append(current)
    return chunks


def chunk_pages(pages: list[PageContent], pdf_tables: list[tuple[int, str]]) -> list[ChunkRecord]:
    size, overlap = config.CHUNK_CHARS, config.CHUNK_OVERLAP
    out: list[ChunkRecord] = []
    ordinal = 0
    for page in pages:
        for piece in _split_text(page.text, size, overlap):
            out.append(
                ChunkRecord(
                    content=piece,
                    page=page.page,
                    ordinal=ordinal,
                    kind=page.kind,
                    token_count=_approx_tokens(piece),
                )
            )
            ordinal += 1
    for page_no, md in pdf_tables:
        out.append(
            ChunkRecord(
                content=md,
                page=page_no,
                ordinal=ordinal,
                kind="table",
                token_count=_approx_tokens(md),
            )
        )
        ordinal += 1
    return [c for c in out if c.content.strip()]
