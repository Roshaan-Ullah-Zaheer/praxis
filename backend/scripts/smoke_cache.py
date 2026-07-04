"""Test the query cache: the same question over the same corpus is served from
cache on the second ask, with zero LLM calls. Run from backend dir:
    python -m scripts.smoke_cache
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import time

from app import llm
from app.agents.runner import run_conversation_stream
from app.ingest.pipeline import ingest_path
from app.store import get_store

OWNER = "demo-user"
QUESTION = "What are the payment terms in the vendor agreement?"


def _seed(store) -> list[str]:
    tmp = tempfile.mkdtemp(prefix="praxis_cache_")
    path = os.path.join(tmp, "vendor_agreement.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("VENDOR SERVICES AGREEMENT\n\nPayment terms: invoices are due Net-30 from the invoice date.\n")
    return [ingest_path(store, OWNER, path, "vendor_agreement.txt", ["legal"])]


async def _ask(conv_id: str) -> tuple[list[str], dict, float]:
    t0 = time.time()
    events = []
    done = {}
    async for ev in run_conversation_stream(conv_id, QUESTION, "legal"):
        events.append(ev["event"])
        if ev["event"] == "done":
            done = json.loads(ev["data"])
    return events, done, time.time() - t0


async def main() -> None:
    if not llm.config.providers_configured():
        raise SystemExit("No LLM providers configured — check backend/.env")
    store = get_store()
    ids = _seed(store)
    try:
        c1 = store.create_conversation(OWNER, "first")
        ev1, done1, t1 = await _ask(c1)
        print(f"run 1 (miss): {t1:.2f}s  cached={done1.get('cached', False)}  answer={done1.get('answer','')[:70]!r}")

        c2 = store.create_conversation(OWNER, "second")
        ev2, done2, t2 = await _ask(c2)
        print(f"run 2 (hit) : {t2:.2f}s  cached={done2.get('cached', False)}  events={ev2}")

        hit = done2.get("cached") is True and "cached" in ev2
        faster = t2 < t1
        same_answer = done1.get("answer") == done2.get("answer")
        print(f"\n[cache hit={hit}, faster={faster} ({t1:.2f}s -> {t2:.2f}s), same answer={same_answer}]")
        print("CACHE SMOKE TEST OK" if (hit and same_answer) else "CACHE SMOKE TEST FAILED")
    finally:
        for doc_id in ids:
            store.delete_document(doc_id)


if __name__ == "__main__":
    asyncio.run(main())
