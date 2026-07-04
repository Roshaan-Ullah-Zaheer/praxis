"""End-to-end smoke test for the M1 ingestion + retrieval path.

Generates a small PDF (text + a table) and a .txt with a deliberate
contradiction, ingests both through the real pipeline (live embeddings via the
multi-key Gemini layer), then runs vector + keyword search to prove the index
works. Run from the backend dir:  python -m scripts.smoke_ingest
"""

from __future__ import annotations

import os
import tempfile

import fitz  # PyMuPDF

from app import llm
from app.ingest.pipeline import ingest_path
from app.store.local import LocalStore


def _make_pdf(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 90), "VENDOR SERVICES AGREEMENT", fontsize=16)
    page.insert_text(
        (72, 130),
        "This agreement sets the commercial terms between Acme Corp and the vendor.\n"
        "Payment terms: all invoices are due Net-30 from the invoice date.\n"
        "Termination requires 60 days written notice by either party.\n"
        "Data retention: customer records are retained for 1 year after termination.",
        fontsize=11,
    )
    page.insert_text((72, 230), "Pricing Schedule:", fontsize=12)
    page.insert_text(
        (72, 255),
        "Tier        Monthly Fee\n"
        "Standard    $1,000\n"
        "Premium     $2,500",
        fontsize=11,
    )
    doc.save(path)
    doc.close()


def _make_txt(path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(
            "MASTER SUPPLY CONTRACT\n\n"
            "Between Acme Corp and the supplier.\n\n"
            "Payment terms: all invoices are due Net-60 from the invoice date.\n\n"
            "Termination requires 30 days written notice.\n\n"
            "Data retention: records are retained indefinitely.\n"
        )


def main() -> None:
    if not llm.config.providers_configured():
        raise SystemExit("No LLM providers configured — check backend/.env")

    tmp = tempfile.mkdtemp(prefix="praxis_smoke_")
    store = LocalStore(os.path.join(tmp, "data"))

    pdf_path = os.path.join(tmp, "vendor_agreement.pdf")
    txt_path = os.path.join(tmp, "supply_contract.txt")
    _make_pdf(pdf_path)
    _make_txt(txt_path)

    print("->ingesting PDF...")
    pdf_id = ingest_path(store, "demo-user", pdf_path, "vendor_agreement.pdf", ["legal"])
    print("->ingesting TXT...")
    txt_id = ingest_path(store, "demo-user", txt_path, "supply_contract.txt", ["legal"])

    for doc_id in (pdf_id, txt_id):
        d = store.get_document(doc_id)
        print(f"   {d.filename:24} status={d.status:8} pages={d.page_count} chunks={d.chunk_count}")
        print(f"   summary: {d.summary[:120]}")

    print("\n->vector search: 'what are the payment terms?'")
    qvec = llm.embed_query("what are the payment terms?")
    for r in store.vector_search("demo-user", qvec, k=4, allowed_roles=["legal"]):
        print(f"   [{r.score:.3f}] {r.filename} p{r.page} ({r.kind}): {r.content[:80].strip()!r}")

    print("\n->keyword search: 'termination notice'")
    for r in store.keyword_search("demo-user", "termination notice", k=4, allowed_roles=["legal"]):
        print(f"   [{r.score:.3f}] {r.filename} p{r.page} ({r.kind}): {r.content[:80].strip()!r}")

    print("\n->governance check: searching as role 'finance' (no access) should return nothing")
    blocked = store.vector_search("demo-user", qvec, k=4, allowed_roles=["finance"])
    print(f"   results visible to 'finance': {len(blocked)}")

    print("\nSMOKE TEST OK" if pdf_id and txt_id else "SMOKE TEST FAILED")


if __name__ == "__main__":
    main()
