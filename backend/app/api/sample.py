"""Sample corpus loader.

One-click ingestion of the bundled neutral-domain documents (vendor agreements,
policies, NDAs, HR handbook) that carry deliberate cross-document contradictions.
Lets the public demo work with zero uploads. No auth required.
"""

from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter, BackgroundTasks

from .. import config
from ..ingest.pipeline import ingest_path
from ..store import get_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sample", tags=["sample"])

SAMPLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sample_data"))


def _load_manifest() -> list[dict]:
    path = os.path.join(SAMPLE_DIR, "manifest.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh).get("documents", [])
    except FileNotFoundError:
        logger.warning("sample manifest not found at %s", path)
        return []


def _ingest_all() -> None:
    store = get_store()
    for entry in _load_manifest():
        src = os.path.join(SAMPLE_DIR, entry["file"])
        if not os.path.exists(src):
            logger.warning("sample document missing: %s", src)
            continue
        try:
            ingest_path(store, config.DEFAULT_OWNER, src, entry["file"], entry.get("roles") or ["public"])
        except Exception as exc:  # noqa: BLE001 - one bad doc shouldn't stop the rest
            logger.warning("failed to ingest sample %s: %s", entry["file"], exc)


@router.post("/load", status_code=202)
def load_sample(background: BackgroundTasks) -> dict:
    """Ingest the bundled sample corpus in the background (idempotent on file hash)."""
    docs = _load_manifest()
    background.add_task(_ingest_all)
    return {"status": "loading", "count": len(docs)}
