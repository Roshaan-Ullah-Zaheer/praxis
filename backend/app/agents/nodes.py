"""Agent graph nodes.

Each node is a pure function: it reads the shared state and returns a partial
update. The same functions power both the streaming SSE runner and plain
``.invoke``. Structured-output nodes use the multi-key LLM layer's failover.
"""

from __future__ import annotations

import logging
import re
from typing import Literal

from pydantic import BaseModel, Field

from .. import llm
from ..retrieval.hybrid import hybrid_retrieve
from ..store import get_store
from .prompts import (
    CONFLICT_SYSTEM,
    RESOLVE_SYSTEM,
    ROUTER_SYSTEM,
    SYNTH_SYSTEM,
    VERIFIER_SYSTEM,
)
from .state import AgentState

logger = logging.getLogger(__name__)

# References that signal a follow-up needing resolution against prior turns.
_REF_PATTERN = re.compile(
    r"\b(it|its|it's|those|them|they|that|these|this|the (?:first|second|third|last|other) one|"
    r"above|previous|earlier|same|both)\b",
    re.IGNORECASE,
)


class RouterDecision(BaseModel):
    intent: Literal["lookup", "crossdoc", "compare", "contradiction", "extract"]
    strategy: Literal["lightweight", "multistep", "graph", "hierarchical"]
    reason: str = Field(description="One sentence explaining the choice.")


class GroundingVerdict(BaseModel):
    grounded: bool
    confidence: float = Field(ge=0.0, le=1.0)
    unsupported: list[str] = Field(default_factory=list)


class DocPosition(BaseModel):
    filename: str
    position: str = Field(description="This document's stance/value on the topic, or that it does not address it.")
    quote: str = ""
    page: int = 0


class ConflictPair(BaseModel):
    document_a: str
    document_b: str
    nature: str = Field(description="The specific disagreement between the two documents.")


class ConflictAnalysis(BaseModel):
    topic: str
    positions: list[DocPosition] = Field(default_factory=list)
    conflicts: list[ConflictPair] = Field(default_factory=list)
    summary: str = ""


# ── helpers ──────────────────────────────────────────────────────────────────
def _format_history(history: list[dict]) -> str:
    if not history:
        return ""
    lines = []
    for turn in history[-6:]:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        lines.append(f"{'User' if role == 'user' else 'Assistant'}: {content}")
    return "Conversation so far:\n" + "\n".join(lines) + "\n\n"


def _format_context(chunks: list[dict]) -> str:
    blocks = [
        f"[{i}] ({c['filename']} p{c['page']}, {c['kind']}) {c['content']}"
        for i, c in enumerate(chunks, 1)
    ]
    return "Context passages:\n" + "\n\n".join(blocks)


def _extract_citations(answer: str, chunks: list[dict]) -> list[dict]:
    nums = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer)})
    out = []
    for n in nums:
        if 1 <= n <= len(chunks):
            c = chunks[n - 1]
            out.append(
                {
                    "n": n,
                    "chunk_id": c["chunk_id"],
                    "document_id": c["document_id"],
                    "filename": c["filename"],
                    "page": c["page"],
                }
            )
    return out


def _q(state: AgentState) -> str:
    """The question to act on — reference-resolved when available."""
    return state.get("resolved_question") or state["question"]


# ── nodes ────────────────────────────────────────────────────────────────────
def resolve_references(state: AgentState) -> dict:
    """Rewrite follow-ups into self-contained questions using the dialogue history.

    Skips the LLM call entirely when there's no history or no reference-like token,
    which keeps simple first questions free.
    """
    question = state["question"]
    history = state.get("history", [])
    if not history or not _REF_PATTERN.search(question):
        return {"resolved_question": question}
    try:
        # Generous ceiling: gemini-2.5-flash spends tokens "thinking"; too small a
        # budget truncates the actual rewrite. The ceiling doesn't raise real cost.
        chat = llm.get_chat(temperature=0.0, max_tokens=1024)
        result = chat.invoke(
            [("system", RESOLVE_SYSTEM), ("user", f"{_format_history(history)}Latest question: {question}")]
        )
        resolved = (result.content or "").strip() or question
        return {"resolved_question": resolved}
    except Exception as exc:  # noqa: BLE001 - fall back to the literal question
        logger.warning("reference resolution failed: %s", exc)
        return {"resolved_question": question}


def route(state: AgentState) -> dict:
    question = _q(state)
    model = llm.get_structured(RouterDecision, temperature=0.0, max_tokens=1024)
    try:
        decision = model.invoke(
            [("system", ROUTER_SYSTEM), ("user", f"{_format_history(state.get('history', []))}Question: {question}")]
        )
        return {
            "intent": decision.intent,
            "strategy": decision.strategy,
            "strategy_reason": decision.reason,
        }
    except Exception as exc:  # noqa: BLE001 - default to a safe, capable route
        logger.warning("router failed, defaulting: %s", exc)
        return {"intent": "lookup", "strategy": "lightweight", "strategy_reason": "default route"}


def retrieve(state: AgentState) -> dict:
    store = get_store()
    k = 6 if state.get("strategy") == "lightweight" else 10
    working_set = state.get("working_set") or None
    hits = hybrid_retrieve(
        store,
        state["owner_id"],
        _q(state),
        k=k,
        allowed_roles=state.get("allowed_roles"),
        document_ids=working_set,
    )
    retrieved = [
        {
            "chunk_id": h.chunk_id,
            "document_id": h.document_id,
            "filename": h.filename,
            "page": h.page,
            "kind": h.kind,
            "content": h.content,
            "score": h.score,
        }
        for h in hits
    ]
    audit = state.get("audit", []) + [
        {"actor": "retriever", "action": "retrieve", "target": f"{len(retrieved)} passages",
         "role_context": state.get("active_role")}
    ]
    return {"retrieved": retrieved, "audit": audit}


def _serialize_hits(hits) -> list[dict]:
    return [
        {"chunk_id": h.chunk_id, "document_id": h.document_id, "filename": h.filename,
         "page": h.page, "kind": h.kind, "content": h.content, "score": h.score}
        for h in hits
    ]


def _render_conflict_answer(summary: str, positions: list[dict], conflicts: list[dict]) -> str:
    lines: list[str] = []
    if summary:
        lines += [summary, ""]
    if conflicts:
        lines.append("**Conflicts found:**")
        for c in conflicts:
            lines.append(f"- {c['document_a']} vs {c['document_b']} — {c['nature']}")
    else:
        lines.append("No contradictions were found among the accessible documents on this topic.")
    if positions:
        lines += ["", "**Each document's position:**"]
        for p in positions:
            quote = f' — "{p["quote"]}"' if p.get("quote") else ""
            lines.append(f"- {p['filename']} (p{p['page']}): {p['position']}{quote}")
    return "\n".join(lines).strip()


def route_intent(state: AgentState) -> str:
    """Send conflict questions down the dedicated detector; everything else is standard."""
    return "conflict" if state.get("intent") == "contradiction" else "standard"


def detect_conflicts(state: AgentState) -> dict:
    """Fan out across documents, extract each one's stance, and compare for conflicts."""
    store = get_store()
    topic = _q(state)
    owner = state["owner_id"]
    roles = state.get("allowed_roles")
    working_set = state.get("working_set") or None
    audit = list(state.get("audit", []))
    empty = {"topic": topic, "positions": [], "conflicts": [], "summary": ""}

    # 1) corpus-wide pass to find which documents are relevant to the topic
    seed = hybrid_retrieve(store, owner, topic, k=12, allowed_roles=roles, document_ids=working_set)
    candidate_ids: list[str] = []
    for h in seed:
        if h.document_id not in candidate_ids:
            candidate_ids.append(h.document_id)
    candidate_ids = candidate_ids[:6]
    if not candidate_ids:
        return {
            "answer": "I couldn't find documents you can access that address that topic to compare.",
            "citations": [], "conflicts": empty, "retrieved": [],
            "grounding": {"grounded": False, "confidence": 0.0, "unsupported": []}, "audit": audit,
        }

    # 2) fan out — retrieve top passages WITHIN each candidate document (no LLM cost)
    doc_blocks: list[str] = []
    fname_to_id: dict[str, str] = {}
    all_hits = []
    for did in candidate_ids:
        hits = hybrid_retrieve(store, owner, topic, k=3, allowed_roles=roles, document_ids=[did])
        if not hits:
            continue
        fname = hits[0].filename
        fname_to_id[fname] = did
        all_hits.extend(hits)
        passages = "\n".join(f"  (p{h.page}) {h.content}" for h in hits)
        doc_blocks.append(f"=== {fname} ===\n{passages}")
        audit.append({"actor": "conflict_detector", "action": "retrieve",
                      "target": f"{fname} ({len(hits)} passages)", "role_context": state.get("active_role")})

    # 3) one structured call extracts each document's stance AND the conflicts
    model = llm.get_structured(ConflictAnalysis, temperature=0.0, max_tokens=2048)
    try:
        analysis = model.invoke(
            [("system", CONFLICT_SYSTEM),
             ("user", f"Topic: {topic}\n\nDocuments and passages:\n" + "\n\n".join(doc_blocks))]
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("conflict analysis failed: %s", exc)
        return {
            "answer": "I found relevant passages but couldn't complete the conflict analysis. Please try again.",
            "citations": [], "conflicts": empty, "retrieved": _serialize_hits(all_hits),
            "grounding": {"grounded": False, "confidence": 0.0, "unsupported": []}, "audit": audit,
        }

    positions = [
        {"filename": p.filename, "document_id": fname_to_id.get(p.filename, ""),
         "position": p.position, "quote": p.quote, "page": p.page}
        for p in analysis.positions
    ]
    conflicts = [{"document_a": c.document_a, "document_b": c.document_b, "nature": c.nature}
                 for c in analysis.conflicts]
    citations = [
        {"n": i, "filename": p["filename"], "document_id": p["document_id"], "page": p["page"], "chunk_id": ""}
        for i, p in enumerate(positions, 1)
    ]
    audit.append({"actor": "conflict_detector", "action": "compare",
                  "target": f"{len(conflicts)} conflict(s) across {len(positions)} document(s)",
                  "role_context": state.get("active_role")})
    return {
        "answer": _render_conflict_answer(analysis.summary, positions, conflicts),
        "citations": citations,
        "conflicts": {"topic": analysis.topic or topic, "positions": positions,
                      "conflicts": conflicts, "summary": analysis.summary},
        "retrieved": _serialize_hits(all_hits),
        "grounding": {"grounded": bool(positions), "confidence": 0.9 if positions else 0.3, "unsupported": []},
        "audit": audit,
    }


def synthesize(state: AgentState) -> dict:
    chunks = state.get("retrieved", [])
    if not chunks:
        return {
            "answer": "I couldn't find anything in the documents you're allowed to see that answers that.",
            "citations": [],
        }
    revise_note = ""
    grounding = state.get("grounding")
    if grounding and not grounding.get("grounded", True):
        unsupported = "; ".join(grounding.get("unsupported", [])) or "some claims"
        revise_note = (
            f"\n\nA previous draft contained unsupported claims ({unsupported}). "
            "Rewrite using ONLY what the passages support; drop anything not backed by them."
        )
    chat = llm.get_chat(temperature=0.2, max_tokens=1500)
    result = chat.invoke(
        [
            ("system", SYNTH_SYSTEM),
            ("user", f"{_format_context(chunks)}\n\nQuestion: {_q(state)}{revise_note}"),
        ]
    )
    answer = (result.content or "").strip()
    return {"answer": answer, "citations": _extract_citations(answer, chunks)}


def verify(state: AgentState) -> dict:
    chunks = state.get("retrieved", [])
    answer = state.get("answer", "")
    if not chunks or not answer:
        return {"grounding": {"grounded": False, "confidence": 0.0, "unsupported": []}}
    model = llm.get_structured(GroundingVerdict, temperature=0.0, max_tokens=1500)
    try:
        verdict = model.invoke(
            [
                ("system", VERIFIER_SYSTEM),
                ("user", f"{_format_context(chunks)}\n\nDrafted answer to check:\n{answer}"),
            ]
        )
        grounding = {
            "grounded": verdict.grounded,
            "confidence": verdict.confidence,
            "unsupported": verdict.unsupported,
        }
    except Exception as exc:  # noqa: BLE001 - if the checker fails, don't block the answer
        logger.warning("verifier failed: %s", exc)
        grounding = {"grounded": True, "confidence": 0.5, "unsupported": []}
    audit = state.get("audit", []) + [
        {"actor": "verifier", "action": "verify",
         "target": f"grounded={grounding['grounded']} conf={grounding['confidence']:.2f}",
         "role_context": state.get("active_role")}
    ]
    return {"grounding": grounding, "audit": audit}


def prepare_revision(state: AgentState) -> dict:
    """Mark that we've taken our one allowed revision pass."""
    return {"revised": True}


def after_verify(state: AgentState) -> str:
    grounding = state.get("grounding", {})
    if not grounding.get("grounded", True) and not state.get("revised"):
        return "revise"
    return "end"
