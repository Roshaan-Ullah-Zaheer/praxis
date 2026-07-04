"""Hybrid retrieval: semantic (vector) + keyword (FTS), fused with RRF.

Reciprocal Rank Fusion is the no-dependency quality baseline — it combines the
two rankings without tuning weights and is robust to score-scale differences
between cosine similarity and BM25. An optional cross-encoder/LLM reranker can be
layered on top later without changing callers.
"""

from __future__ import annotations

from .. import llm
from ..store.base import RetrievedChunk, Store


def reciprocal_rank_fusion(
    result_lists: list[list[RetrievedChunk]], k: int = 60
) -> list[RetrievedChunk]:
    """Fuse several ranked lists into one. Higher fused score = better."""
    scores: dict[str, float] = {}
    best: dict[str, RetrievedChunk] = {}
    for results in result_lists:
        for rank, item in enumerate(results):
            scores[item.chunk_id] = scores.get(item.chunk_id, 0.0) + 1.0 / (k + rank + 1)
            best.setdefault(item.chunk_id, item)
    fused = [
        RetrievedChunk(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            filename=c.filename,
            page=c.page,
            kind=c.kind,
            content=c.content,
            score=scores[c.chunk_id],
        )
        for c in best.values()
    ]
    fused.sort(key=lambda c: c.score, reverse=True)
    return fused


def hybrid_retrieve(
    store: Store,
    owner_id: str,
    query: str,
    k: int = 8,
    allowed_roles: list[str] | None = None,
    document_ids: list[str] | None = None,
    pool: int = 20,
) -> list[RetrievedChunk]:
    """Embed the query, run vector + keyword search, fuse, and return top-k."""
    query_embedding = llm.embed_query(query)
    vector_hits = store.vector_search(
        owner_id, query_embedding, k=pool, allowed_roles=allowed_roles, document_ids=document_ids
    )
    keyword_hits = store.keyword_search(
        owner_id, query, k=pool, allowed_roles=allowed_roles, document_ids=document_ids
    )
    return reciprocal_rank_fusion([vector_hits, keyword_hits])[:k]
