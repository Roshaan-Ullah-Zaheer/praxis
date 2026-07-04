"""Streaming runner: drives the agent graph and emits glass-box SSE events.

Each LangGraph node update is translated into a typed event the frontend uses to
animate the live pipeline (which agent is working, the chosen strategy, what was
retrieved, the answer, the grounding verdict, the audit trail). Dialogue memory
is loaded before the run and persisted after.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from .. import config, llm
from ..cache.query_cache import corpus_signature, make_key
from ..store import get_store
from ..web.search import web_search
from .graph import get_graph
from .memory import load_dialogue, maybe_compress, update_working_set
from .prompts import WEB_SYNTH_SYSTEM

logger = logging.getLogger(__name__)


def _sse(event: str, payload: dict) -> dict:
    return {"event": event, "data": json.dumps(payload)}


async def _replay_cached(store, conversation_id: str, payload: dict) -> AsyncIterator[dict]:
    """Stream a cached answer as a compact event sequence (no LLM calls)."""
    yield _sse("cached", {"hit": True})
    yield _sse("agent_step", {"agent": "orchestrator", "status": "running"})
    if payload.get("strategy") or payload.get("intent"):
        yield _sse(
            "strategy_selected",
            {"intent": payload.get("intent"), "strategy": payload.get("strategy"),
             "reason": "served from cache"},
        )
    retrieval = payload.get("retrieval") or []
    if retrieval:
        yield _sse("retrieval", {"count": len(retrieval), "chunks": retrieval})
    conflicts = payload.get("conflicts") or {}
    if conflicts.get("conflicts"):
        yield _sse("conflict", conflicts)
    yield _sse("answer", {"text": payload.get("answer", ""), "citations": payload.get("citations", [])})
    yield _sse("grounding", payload.get("grounding", {}))
    message_id = store.add_message(
        conversation_id, "assistant", payload.get("answer", ""),
        strategy=payload.get("strategy"), grounding=payload.get("grounding"),
        confidence=(payload.get("grounding") or {}).get("confidence"),
        sources=payload.get("sources", []),
    )
    update_working_set(store, conversation_id, [], payload.get("citations", []))
    yield _sse("done", {**payload, "message_id": message_id, "cached": True})


def _events_for(node: str, delta: dict) -> list[dict]:
    events: list[dict] = []
    if node == "resolver":
        resolved = delta.get("resolved_question")
        events.append(_sse("agent_step", {"agent": "resolver", "status": "done"}))
        if resolved:
            events.append(_sse("resolved", {"resolved_question": resolved}))
    elif node == "router":
        events.append(_sse("agent_step", {"agent": "router", "status": "done"}))
        events.append(
            _sse(
                "strategy_selected",
                {
                    "intent": delta.get("intent"),
                    "strategy": delta.get("strategy"),
                    "reason": delta.get("strategy_reason"),
                },
            )
        )
    elif node == "retriever":
        chunks = delta.get("retrieved", [])
        events.append(_sse("agent_step", {"agent": "retriever", "status": "done"}))
        events.append(
            _sse(
                "retrieval",
                {
                    "count": len(chunks),
                    "chunks": [
                        {"filename": c["filename"], "page": c["page"], "kind": c["kind"],
                         "score": round(c["score"], 4)}
                        for c in chunks
                    ],
                },
            )
        )
    elif node == "synthesizer":
        events.append(_sse("agent_step", {"agent": "synthesizer", "status": "done"}))
        events.append(
            _sse("answer", {"text": delta.get("answer", ""), "citations": delta.get("citations", [])})
        )
    elif node == "conflict_detector":
        events.append(_sse("agent_step", {"agent": "conflict_detector", "status": "done"}))
        events.append(_sse("conflict", delta.get("conflicts", {})))
        events.append(
            _sse("answer", {"text": delta.get("answer", ""), "citations": delta.get("citations", [])})
        )
        events.append(_sse("grounding", delta.get("grounding", {})))
    elif node == "verifier":
        events.append(_sse("agent_step", {"agent": "verifier", "status": "done"}))
        events.append(_sse("grounding", delta.get("grounding", {})))
    elif node == "reviser":
        events.append(_sse("agent_step", {"agent": "reviser", "status": "revising"}))
    return events


def _synth_from_web(question: str, results: list[dict]) -> str:
    """Compose a clearly-labeled answer from web results when the corpus had none."""
    blocks = "\n\n".join(
        f"[{i}] {r['title']} ({r['url']})\n{r['content']}" for i, r in enumerate(results, 1)
    )
    chat = llm.get_chat(temperature=0.3, max_tokens=1200)
    out = chat.invoke([("system", WEB_SYNTH_SYSTEM), ("user", f"Question: {question}\n\nWeb results:\n{blocks}")])
    return (out.content or "").strip()


async def run_conversation_stream(
    conversation_id: str,
    question: str,
    active_role: str | None = None,
    allow_web: bool = False,
) -> AsyncIterator[dict]:
    store = get_store()
    conv = store.get_conversation(conversation_id)
    if not conv:
        yield _sse("error", {"message": "conversation not found"})
        return

    history, working_set = load_dialogue(store, conversation_id)
    store.add_message(conversation_id, "user", question)
    allowed_roles = [active_role] if active_role else None

    # Query cache: identical question over the same corpus + role + focus is served
    # instantly with zero LLM calls.
    corpus_sig = corpus_signature(store, conv["owner_id"], allowed_roles)
    cache_key = make_key(question, active_role, corpus_sig, working_set)
    cached = store.get_cached_query(cache_key)
    if cached:
        async for event in _replay_cached(store, conversation_id, cached):
            yield event
        return

    state = {
        "owner_id": conv["owner_id"],
        "conversation_id": conversation_id,
        "question": question,
        "active_role": active_role,
        "allowed_roles": allowed_roles,
        "history": history,
        "working_set": working_set,
        "audit": [],
    }

    yield _sse("agent_step", {"agent": "orchestrator", "status": "running"})

    final: dict = {}
    graph = get_graph()
    try:
        # Dual stream: "messages" surfaces synthesizer tokens for a live typing
        # effect; "updates" carries the per-node state used to drive the pipeline.
        async for mode, data in graph.astream(state, stream_mode=["updates", "messages"]):
            if mode == "messages":
                chunk, metadata = data
                if metadata.get("langgraph_node") == "synthesizer":
                    content = getattr(chunk, "content", "")
                    delta = content if isinstance(content, str) else ""
                    if delta:
                        yield _sse("token", {"delta": delta})
                continue
            for node, delta in data.items():
                if delta:
                    final.update(delta)
                    for event in _events_for(node, delta):
                        yield event
    except Exception as exc:  # noqa: BLE001 - never leave the client hanging
        yield _sse("error", {"message": f"The assistant hit an error: {exc}"})
        return

    answer = final.get("answer", "")
    citations = final.get("citations", [])
    grounding = final.get("grounding", {})
    retrieved = final.get("retrieved", [])
    audit = final.get("audit", [])

    # Web augmentation (opt-in): only when the corpus returned nothing. The core
    # graph is untouched — this is a clearly-labeled fallback layered on top.
    web_sources: list[dict] = []
    if allow_web and not retrieved:
        results = web_search(question)
        if results:
            yield _sse("agent_step", {"agent": "web", "status": "running"})
            try:
                answer = _synth_from_web(question, results) or answer
                web_sources = [{"title": r["title"], "url": r["url"]} for r in results]
                grounding = {"grounded": False, "confidence": 0.0, "unsupported": [], "source": "web"}
                audit = audit + [
                    {"actor": "web", "action": "web", "target": f"{len(results)} web result(s)",
                     "role_context": active_role}
                ]
                yield _sse("web", {"sources": web_sources})
                yield _sse("answer", {"text": answer, "citations": []})
                yield _sse("grounding", grounding)
            except Exception as exc:  # noqa: BLE001 - fall back to the corpus refusal
                logger.warning("web augmentation failed: %s", exc)

    by_id = {c["chunk_id"]: c for c in retrieved}
    sources = [
        {
            "chunk_id": cit["chunk_id"],
            "document_id": cit["document_id"],
            "page": cit["page"],
            "snippet": by_id.get(cit["chunk_id"], {}).get("content", "")[:240],
        }
        for cit in citations
    ]
    message_id = store.add_message(
        conversation_id,
        "assistant",
        answer,
        strategy=final.get("strategy"),
        grounding=grounding,
        confidence=grounding.get("confidence"),
        sources=sources,
    )
    if audit:
        store.add_audit(conversation_id, message_id, audit)
    update_working_set(store, conversation_id, retrieved, citations)
    maybe_compress(store, conversation_id)

    payload = {
        "message_id": message_id,
        "intent": final.get("intent"),
        "strategy": final.get("strategy"),
        "answer": answer,
        "citations": citations,
        "grounding": grounding,
        "conflicts": final.get("conflicts", {}),
        "audit": audit,
        "sources": sources,
        "web_sources": web_sources,
        "retrieval": [
            {"filename": c["filename"], "page": c["page"], "kind": c["kind"],
             "score": round(c["score"], 4)}
            for c in retrieved
        ],
    }
    # Cache only confident, grounded answers — never failures or refusals.
    if answer and grounding.get("grounded"):
        store.set_cached_query(cache_key, payload)

    yield _sse("done", payload)
