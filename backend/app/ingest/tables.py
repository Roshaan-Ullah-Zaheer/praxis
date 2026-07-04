"""Table extraction (PDF) into Markdown so the LLM reads tabular data faithfully."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _to_markdown(rows: list[list]) -> str:
    rows = [[("" if c is None else str(c)).replace("\n", " ").strip() for c in row] for row in rows]
    rows = [r for r in rows if any(cell for cell in r)]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    header, *body = rows
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * width) + " |"]
    out += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(out)


def extract_pdf_tables(path: str) -> list[tuple[int, str]]:
    """Return ``(page_number, markdown_table)`` for every table found in a PDF."""
    out: list[tuple[int, str]] = []
    try:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                for table in page.extract_tables() or []:
                    md = _to_markdown(table)
                    if md:
                        out.append((i, md))
    except Exception as exc:  # noqa: BLE001 - never let table extraction break ingestion
        logger.warning("table extraction failed for %s: %s", path, exc)
    return out
