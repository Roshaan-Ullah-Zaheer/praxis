"""End-to-end smoke test for the M3 agent harness.

Ingests two contradicting contracts into the default local store, then runs the
full LangGraph pipeline on a cross-document question and prints the route, the
grounded answer with citations, and the grounding verdict. Run from backend dir:
    python -m scripts.smoke_agent
"""

from __future__ import annotations

import os
import tempfile

from app import llm
from app.agents.graph import get_graph
from app.ingest.pipeline import ingest_path
from app.store import get_store

OWNER = "agent-test"


def _seed(store) -> list[str]:
    tmp = tempfile.mkdtemp(prefix="praxis_agent_")
    a = os.path.join(tmp, "vendor_agreement.txt")
    b = os.path.join(tmp, "supply_contract.txt")
    with open(a, "w", encoding="utf-8") as fh:
        fh.write(
            "VENDOR SERVICES AGREEMENT\n\n"
            "Payment terms: all invoices are due Net-30 from the invoice date.\n\n"
            "Termination requires 60 days written notice by either party.\n"
        )
    with open(b, "w", encoding="utf-8") as fh:
        fh.write(
            "MASTER SUPPLY CONTRACT\n\n"
            "Payment terms: all invoices are due Net-60 from the invoice date.\n\n"
            "Termination requires 30 days written notice.\n"
        )
    return [
        ingest_path(store, OWNER, a, "vendor_agreement.txt", ["legal"]),
        ingest_path(store, OWNER, b, "supply_contract.txt", ["legal"]),
    ]


def main() -> None:
    if not llm.config.providers_configured():
        raise SystemExit("No LLM providers configured — check backend/.env")

    store = get_store()
    ids = _seed(store)
    try:
        graph = get_graph()
        result = graph.invoke(
            {
                "owner_id": OWNER,
                "question": "What are the payment terms in these contracts, and do they agree?",
                "allowed_roles": ["legal"],
                "active_role": "legal",
                "history": [],
                "working_set": [],
                "audit": [],
            }
        )
        print(f"intent     : {result.get('intent')}")
        print(f"strategy   : {result.get('strategy')}  ({result.get('strategy_reason')})")
        print(f"\nanswer:\n{result.get('answer')}")
        print(f"\ncitations  : {[(c['n'], c['filename'], 'p%d' % c['page']) for c in result.get('citations', [])]}")
        g = result.get("grounding", {})
        print(f"grounding  : grounded={g.get('grounded')} confidence={g.get('confidence')}")
        print(f"audit steps: {[a['actor'] for a in result.get('audit', [])]}")
        ok = bool(result.get("answer")) and result.get("citations")
        print("\nAGENT SMOKE TEST OK" if ok else "\nAGENT SMOKE TEST FAILED")
    finally:
        for doc_id in ids:
            store.delete_document(doc_id)


if __name__ == "__main__":
    main()
