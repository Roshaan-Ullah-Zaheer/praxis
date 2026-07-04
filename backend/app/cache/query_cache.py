"""Semantic-exact query cache.

Keyed on the normalized question + active role + a signature of the visible
corpus + the conversation's working set. A repeated question over the same
documents and role returns instantly with zero LLM calls — the single biggest
cost saver for the public demo, where everyone asks the same sample questions.

The corpus signature changes when documents are added/removed, which naturally
invalidates stale answers.
"""

from __future__ import annotations

import hashlib

from ..store.base import Store


def corpus_signature(store: Store, owner_id: str, allowed_roles: list[str] | None) -> str:
    docs = store.list_documents(owner_id)
    visible = sorted(
        d.id
        for d in docs
        if d.status == "ready" and (not allowed_roles or set(allowed_roles) & set(d.roles))
    )
    return hashlib.sha256(",".join(visible).encode()).hexdigest()[:16]


def make_key(
    question: str, active_role: str | None, corpus_sig: str, working_set: list[str] | None
) -> str:
    norm = " ".join(question.lower().split())
    raw = f"{norm}|{active_role or ''}|{corpus_sig}|{','.join(working_set or [])}"
    return hashlib.sha256(raw.encode()).hexdigest()
