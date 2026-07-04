"""Governance API: the roles present in the corpus (for the role switcher) and
the per-role visibility overview. Retrieval is already role-filtered in the store,
and audit is exposed per-conversation under /conversations/{id}/audit.
"""

from __future__ import annotations

from fastapi import APIRouter

from .. import config
from ..store import get_store

router = APIRouter(prefix="/governance", tags=["governance"])


@router.get("/roles")
def list_roles() -> list[dict]:
    """Distinct roles across the corpus with how many documents each can see."""
    docs = get_store().list_documents(config.DEFAULT_OWNER)
    counts: dict[str, int] = {}
    for d in docs:
        for role in d.roles or []:
            counts[role] = counts.get(role, 0) + 1
    return [{"role": role, "document_count": counts[role]} for role in sorted(counts)]


@router.get("/overview")
def overview() -> dict:
    """Per-role view of which documents are visible — powers the governance demo."""
    docs = get_store().list_documents(config.DEFAULT_OWNER)
    roles: dict[str, list[dict]] = {}
    for d in docs:
        for role in d.roles or []:
            roles.setdefault(role, []).append({"id": d.id, "filename": d.filename})
    return {
        "total_documents": len(docs),
        "roles": [
            {"role": role, "documents": roles[role], "document_count": len(roles[role])}
            for role in sorted(roles)
        ],
    }
