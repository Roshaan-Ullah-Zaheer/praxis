"""Optional live web augmentation via Tavily.

Used only as a clearly-labeled fallback when the document corpus can't answer and
the user has opted in. Uses the stdlib HTTP client so no extra dependency is
required on the deploy image.
"""

from __future__ import annotations

import json
import logging
import urllib.request

from .. import config

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.tavily.com/search"


def web_available() -> bool:
    return bool(config.TAVILY_API_KEY)


def web_search(query: str, max_results: int = 5, timeout: float = 12.0) -> list[dict]:
    """Return [{title, url, content}] from Tavily, or [] on any failure."""
    if not config.TAVILY_API_KEY:
        return []
    payload = json.dumps(
        {
            "api_key": config.TAVILY_API_KEY,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        _ENDPOINT, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - augmentation is best-effort
        logger.warning("web search failed: %s", exc)
        return []
    results = []
    for r in data.get("results", [])[:max_results]:
        results.append(
            {
                "title": r.get("title", "Untitled"),
                "url": r.get("url", ""),
                "content": (r.get("content") or "").strip(),
            }
        )
    return results
