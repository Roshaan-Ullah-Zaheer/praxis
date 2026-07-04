"""Conversation (dialogue) memory.

Distinct from the document/retrieval memory: this tracks the running dialogue so
follow-ups resolve against it. Older turns are compressed into a rolling summary
once the thread grows, so token cost stays flat on long conversations.
"""

from __future__ import annotations

import json
import logging

from .. import llm
from ..store.base import Store
from .prompts import SUMMARY_SYSTEM

logger = logging.getLogger(__name__)

RECENT_TURNS = 4          # full turns kept verbatim (user+assistant pairs)
COMPRESS_AFTER = 10       # message count beyond which older turns are summarized


def load_dialogue(store: Store, conversation_id: str) -> tuple[list[dict], list[str]]:
    """Return (history, working_set) for the agent — summary + recent turns."""
    conv = store.get_conversation(conversation_id) or {}
    summary = conv.get("summary") or ""
    working_set = json.loads(conv.get("working_set") or "[]")
    messages = store.get_messages(conversation_id)
    recent = messages[-(RECENT_TURNS * 2):]

    history: list[dict] = []
    if summary:
        history.append({"role": "assistant", "content": f"[Earlier conversation summary] {summary}"})
    history.extend({"role": m["role"], "content": m["content"]} for m in recent)
    return history, working_set


def update_working_set(
    store: Store, conversation_id: str, retrieved: list[dict], citations: list[dict]
) -> None:
    """Track the documents currently in focus so 'those/them' can scope to them."""
    ids = [c["document_id"] for c in citations] or [r["document_id"] for r in retrieved[:5]]
    seen: list[str] = []
    for i in ids:
        if i and i not in seen:
            seen.append(i)
    if seen:
        store.update_conversation(conversation_id, working_set=json.dumps(seen))


def maybe_compress(store: Store, conversation_id: str) -> None:
    """Fold older turns into a rolling summary once the thread is long."""
    messages = store.get_messages(conversation_id)
    if len(messages) <= COMPRESS_AFTER:
        return
    older = messages[: -(RECENT_TURNS * 2)]
    if not older:
        return
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in older)[:8000]
    try:
        chat = llm.get_chat(temperature=0.2, max_tokens=700)
        result = chat.invoke([("system", SUMMARY_SYSTEM), ("user", transcript)])
        summary = (result.content or "").strip()
        if summary:
            store.update_conversation(conversation_id, summary=summary)
    except Exception as exc:  # noqa: BLE001 - summary is best-effort
        logger.warning("conversation compression failed: %s", exc)
