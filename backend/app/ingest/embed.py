"""Embedding with a content-hash cache.

Identical chunk text is embedded once and reused across documents and re-uploads,
which is the single biggest embedding-cost saver. Uncached chunks are embedded in
batches through the multi-key Gemini layer.
"""

from __future__ import annotations

import hashlib

from .. import llm
from ..store.base import ChunkRecord
from ..store.base import Store

_BATCH = 50


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def embed_chunks(chunks: list[ChunkRecord], store: Store) -> list[ChunkRecord]:
    pending_text: list[str] = []
    pending_idx: list[int] = []
    pending_hash: list[str] = []

    for i, chunk in enumerate(chunks):
        h = _hash(chunk.content)
        cached = store.get_cached_embedding(h)
        if cached is not None:
            chunk.embedding = cached
        else:
            pending_text.append(chunk.content)
            pending_idx.append(i)
            pending_hash.append(h)

    for start in range(0, len(pending_text), _BATCH):
        batch = pending_text[start : start + _BATCH]
        vectors = llm.embed_documents(batch)
        for offset, vec in enumerate(vectors):
            idx = pending_idx[start + offset]
            chunks[idx].embedding = vec
            store.cache_embedding(pending_hash[start + offset], vec)

    return chunks
