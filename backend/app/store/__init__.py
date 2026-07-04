"""Storage backend factory.

Praxis is storage-agnostic. ``local`` runs the whole app with zero external
infra (SQLite FTS5 + NumPy vectors + local files); ``supabase`` swaps in a
production Postgres + pgvector backend without touching the rest of the code.
"""

from __future__ import annotations

from .. import config
from .base import Store

_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        if config.STORE_BACKEND == "supabase":
            raise NotImplementedError("Supabase backend lands in M8/deploy; use STORE_BACKEND=local.")
        from .local import LocalStore

        _store = LocalStore(config.LOCAL_DATA_DIR)
    return _store
