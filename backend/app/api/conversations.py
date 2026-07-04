"""Conversations API: create, list, fetch history, the streaming chat endpoint,
and a sourced Markdown export of an analysis."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Body, HTTPException, Response
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .. import config
from ..agents.runner import run_conversation_stream
from ..store import get_store

router = APIRouter(prefix="/conversations", tags=["conversations"])


class MessageIn(BaseModel):
    question: str
    active_role: str | None = None
    allow_web: bool = False


@router.post("", status_code=201)
def create_conversation(title: str = Body("New conversation", embed=True)) -> dict:
    store = get_store()
    conv_id = store.create_conversation(config.DEFAULT_OWNER, title)
    return store.get_conversation(conv_id)  # type: ignore[return-value]


@router.get("")
def list_conversations() -> list[dict]:
    return get_store().list_conversations(config.DEFAULT_OWNER)


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str) -> dict:
    store = get_store()
    conv = store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(404, "conversation not found")
    return {**conv, "messages": store.get_messages(conversation_id)}


@router.get("/{conversation_id}/audit")
def get_audit(conversation_id: str) -> list[dict]:
    return get_store().get_audit(conversation_id)


@router.post("/{conversation_id}/messages")
async def post_message(conversation_id: str, payload: MessageIn) -> EventSourceResponse:
    store = get_store()
    if not store.get_conversation(conversation_id):
        raise HTTPException(404, "conversation not found")
    return EventSourceResponse(
        run_conversation_stream(
            conversation_id, payload.question, payload.active_role, payload.allow_web
        )
    )


def _doc_name(store, cache: dict, document_id: str) -> str:
    if document_id not in cache:
        doc = store.get_document(document_id) if document_id else None
        cache[document_id] = doc.filename if doc else (document_id or "unknown source")
    return cache[document_id]


def _render_report(conv: dict, messages: list[dict], store) -> str:
    title = conv.get("title") or "Conversation"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Praxis Report — {title}",
        "",
        f"_Generated {stamp} · governed multi-agent document intelligence_",
    ]
    if conv.get("active_role"):
        lines.append(f"_Role context: {conv['active_role']}_")
    lines += ["", "---", ""]

    cache: dict[str, str] = {}
    question_no = 0
    for m in messages:
        if m["role"] == "user":
            question_no += 1
            lines += [f"## {question_no}. {m['content']}", ""]
            continue

        lines += [m.get("content") or "_No answer was produced._", ""]

        grounding = m.get("grounding") or {}
        meta: list[str] = []
        if m.get("strategy"):
            meta.append(f"strategy: {m['strategy']}")
        if grounding:
            verdict = "grounded" if grounding.get("grounded") else "unsupported"
            conf = grounding.get("confidence")
            if isinstance(conf, (int, float)):
                verdict += f" ({round(conf * 100)}%)"
            meta.append(f"grounding: {verdict}")
        if meta:
            lines += ["> " + " · ".join(meta), ""]

        sources = m.get("sources") or []
        if sources:
            lines.append("**Sources**")
            for i, s in enumerate(sources, 1):
                name = _doc_name(store, cache, s.get("document_id", ""))
                page = s.get("page")
                loc = f" p.{page}" if page else ""
                snippet = (s.get("snippet") or "").replace("\n", " ").strip()
                tail = f' — "{snippet}"' if snippet else ""
                lines.append(f"- [{i}] {name}{loc}{tail}")
            lines.append("")

        lines += ["---", ""]

    lines.append("_Exported from Praxis._")
    return "\n".join(lines)


@router.get("/{conversation_id}/export")
def export_conversation(conversation_id: str) -> Response:
    """Download the conversation as a sourced Markdown report."""
    store = get_store()
    conv = store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(404, "conversation not found")
    markdown = _render_report(conv, store.get_messages(conversation_id), store)
    filename = f"praxis-report-{conversation_id[:8]}.md"
    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
