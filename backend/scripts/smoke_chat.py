"""End-to-end test for the SSE runner + M4 conversation memory.

Runs a two-turn conversation through the streaming runner. Turn 2 uses a pronoun
('those') that only resolves via the prior turn — proving reference resolution
and working-set memory, plus the full glass-box event stream. Run from backend:
    python -m scripts.smoke_chat
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile

from app import llm
from app.agents.runner import run_conversation_stream
from app.ingest.pipeline import ingest_path
from app.store import get_store

OWNER = "demo-user"


def _seed(store) -> list[str]:
    tmp = tempfile.mkdtemp(prefix="praxis_chat_")
    a = os.path.join(tmp, "vendor_agreement.txt")
    b = os.path.join(tmp, "supply_contract.txt")
    with open(a, "w", encoding="utf-8") as fh:
        fh.write("VENDOR SERVICES AGREEMENT\n\nPayment terms: invoices are due Net-30 from the invoice date.\n")
    with open(b, "w", encoding="utf-8") as fh:
        fh.write("MASTER SUPPLY CONTRACT\n\nPayment terms: invoices are due Net-60 from the invoice date.\n")
    return [
        ingest_path(store, OWNER, a, "vendor_agreement.txt", ["legal"]),
        ingest_path(store, OWNER, b, "supply_contract.txt", ["legal"]),
    ]


async def _run_turn(conv_id: str, question: str) -> list[tuple[str, dict]]:
    events = []
    async for ev in run_conversation_stream(conv_id, question, active_role="legal"):
        events.append((ev["event"], json.loads(ev["data"])))
    return events


def _show(label: str, events: list[tuple[str, dict]]) -> None:
    print(f"\n=== {label} ===")
    seen = [e for e, _ in events]
    print("event stream:", " -> ".join(seen))
    for name, data in events:
        if name == "resolved":
            print("  resolved_question:", data["resolved_question"])
        elif name == "strategy_selected":
            print(f"  route: intent={data['intent']} strategy={data['strategy']}")
        elif name == "done":
            print("  answer:", data["answer"])
            print("  grounding:", data["grounding"])


async def main() -> None:
    if not llm.config.providers_configured():
        raise SystemExit("No LLM providers configured — check backend/.env")
    store = get_store()
    ids = _seed(store)
    conv_id = store.create_conversation(OWNER, "Contract review")
    try:
        t1 = await _run_turn(conv_id, "What are the payment terms in these contracts?")
        _show("TURN 1", t1)
        t2 = await _run_turn(conv_id, "Which of those is more aggressive for the buyer?")
        _show("TURN 2 (pronoun 'those')", t2)

        conv = store.get_conversation(conv_id)
        msgs = store.get_messages(conv_id)
        print(f"\npersisted messages: {len(msgs)}  working_set: {conv['working_set']}")
        resolved_in_t2 = any(e == "resolved" for e, _ in t2)
        answered = any(e == "done" and d["answer"] for e, d in t2)
        print("\nCHAT/MEMORY SMOKE TEST OK" if (len(msgs) == 4 and resolved_in_t2 and answered)
              else "\nCHAT/MEMORY SMOKE TEST FAILED")
    finally:
        for doc_id in ids:
            store.delete_document(doc_id)


if __name__ == "__main__":
    asyncio.run(main())
