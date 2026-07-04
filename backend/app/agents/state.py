"""Shared state for the Praxis agent graph.

One typed dict flows through every node; each node returns a partial update that
LangGraph merges. Keeping dialogue memory (history, working_set) separate from
retrieval results is deliberate — the two memories feed the agents independently.
"""

from __future__ import annotations

from typing import Any, Optional, TypedDict


class AgentState(TypedDict, total=False):
    # request / governance
    owner_id: str
    conversation_id: str
    active_role: Optional[str]
    allowed_roles: Optional[list[str]]

    # dialogue memory
    question: str
    resolved_question: str
    history: list[dict[str, Any]]
    working_set: list[str]  # document ids currently in focus

    # routing
    intent: str
    strategy: str
    strategy_reason: str

    # retrieval + analysis
    retrieved: list[dict[str, Any]]
    answer: str
    citations: list[dict[str, Any]]

    # cross-document conflict analysis (M6)
    conflicts: dict[str, Any]

    # verification / control
    grounding: dict[str, Any]
    revised: bool
    audit: list[dict[str, Any]]
