"""End-to-end test for M6 cross-document contradiction detection.

Ingests three contracts with conflicting payment terms (Net-30 / Net-45 / Net-60)
and one unrelated HR policy, then asks which documents contradict each other. The
conflict detector should surface the per-document positions and the conflicting
pairs. Run from backend dir:  python -m scripts.smoke_conflict
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

DOCS = {
    "alpha_vendor_agreement.txt": "ALPHA VENDOR AGREEMENT\n\nPayment terms: all invoices are due Net-30 from the invoice date.\n",
    "beta_supply_contract.txt": "BETA SUPPLY CONTRACT\n\nPayment terms: all invoices are due Net-45 from the invoice date.\n",
    "gamma_master_services.txt": "GAMMA MASTER SERVICES AGREEMENT\n\nPayment terms: all invoices are due Net-60 from the invoice date.\n",
    "hr_leave_policy.txt": "HR LEAVE POLICY\n\nEmployees accrue 20 days of paid annual leave per year.\n",
}


def _seed(store) -> list[str]:
    tmp = tempfile.mkdtemp(prefix="praxis_conflict_")
    ids = []
    for name, text in DOCS.items():
        path = os.path.join(tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        ids.append(ingest_path(store, OWNER, path, name, ["legal"]))
    return ids


async def main() -> None:
    if not llm.config.providers_configured():
        raise SystemExit("No LLM providers configured — check backend/.env")
    store = get_store()
    ids = _seed(store)
    conv_id = store.create_conversation(OWNER, "Conflict review")
    try:
        events = []
        async for ev in run_conversation_stream(
            conv_id, "Which of these documents contradict each other on payment terms?", "legal"
        ):
            events.append((ev["event"], json.loads(ev["data"])))

        print("event stream:", " -> ".join(e for e, _ in events))
        done = next((d for e, d in events if e == "done"), {})
        print(f"\nintent: {done.get('intent')}")
        conflicts = done.get("conflicts", {})
        print(f"\nsummary: {conflicts.get('summary')}")
        print("\npositions:")
        for p in conflicts.get("positions", []):
            print(f"  - {p['filename']} (p{p['page']}): {p['position']}")
        print("\nconflicts:")
        for c in conflicts.get("conflicts", []):
            print(f"  - {c['document_a']} vs {c['document_b']}: {c['nature']}")

        had_conflict_event = any(e == "conflict" for e, _ in events)
        n_conflicts = len(conflicts.get("conflicts", []))
        n_positions = len(conflicts.get("positions", []))
        ok = had_conflict_event and n_conflicts >= 1 and n_positions >= 3
        print(f"\n[conflict event={had_conflict_event}, conflicts={n_conflicts}, positions={n_positions}]")
        print("CONFLICT SMOKE TEST OK" if ok else "CONFLICT SMOKE TEST FAILED")
    finally:
        for doc_id in ids:
            store.delete_document(doc_id)


if __name__ == "__main__":
    asyncio.run(main())
