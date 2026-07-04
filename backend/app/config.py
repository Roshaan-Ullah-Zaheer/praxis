"""Runtime configuration, loaded from the environment.

Provider keys, model names, and service credentials live here. The LLM access
layer follows a multi-key Gemini -> Groq fallback: ``GOOGLE_API_KEYS`` holds a
comma-separated list of keys that are rotated for throughput and failover, with
Groq as the final fallback when every Gemini key is exhausted.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _csv(name: str) -> list[str]:
    """Parse a comma-separated env var into a clean list of values."""
    return [part.strip() for part in os.getenv(name, "").split(",") if part.strip()]


# ── LLM providers ────────────────────────────────────────────────────────────
GOOGLE_API_KEYS: list[str] = _csv("GOOGLE_API_KEYS")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()

GEMINI_CHAT_MODEL: str = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash")
GEMINI_CHAT_FALLBACK: str = os.getenv("GEMINI_CHAT_FALLBACK", "gemini-2.5-flash-lite")
GROQ_CHAT_MODEL: str = os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")

EMBED_MODEL: str = os.getenv("EMBED_MODEL", "models/gemini-embedding-001")
EMBED_DIM: int = int(os.getenv("EMBED_DIM", "768"))

# ── Data / services (used from M1) ───────────────────────────────────────────
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
DATABASE_URL: str = os.getenv("DATABASE_URL", "").strip()

# ── Auth (used from M8) ──────────────────────────────────────────────────────
# When set, a Supabase JWT in the Authorization header is verified and its user
# id becomes the owner; otherwise the app runs in single-user demo mode.
SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "").strip()

# ── Payments (used from M8) ──────────────────────────────────────────────────
STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
STRIPE_PRICE_PRO: str = os.getenv("STRIPE_PRICE_PRO", "").strip()
STRIPE_PRICE_ENTERPRISE: str = os.getenv("STRIPE_PRICE_ENTERPRISE", "").strip()
# Where Stripe Checkout returns the user after success/cancel.
FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000").strip()

# ── Web augmentation (used from M10) ─────────────────────────────────────────
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "").strip()

# ── Storage backend ──────────────────────────────────────────────────────────
# "local"  -> SQLite (FTS5) + NumPy vectors + local files (zero external infra)
# "supabase" -> Postgres + pgvector + Supabase Auth/Storage (production)
STORE_BACKEND: str = os.getenv("STORE_BACKEND", "local").strip().lower()
LOCAL_DATA_DIR: str = os.getenv("LOCAL_DATA_DIR", "./data").strip()

# ── Retrieval tuning ─────────────────────────────────────────────────────────
CHUNK_CHARS: int = int(os.getenv("CHUNK_CHARS", "3000"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "300"))

# ── App ──────────────────────────────────────────────────────────────────────
CORS_ORIGINS: list[str] = _csv("CORS_ORIGINS") or ["http://localhost:3000"]
PORT: int = int(os.getenv("PORT", "7860"))

# Default owner used until auth lands (M8).
DEFAULT_OWNER: str = "demo-user"


def providers_configured() -> bool:
    """True when at least one text LLM provider is available."""
    return bool(GOOGLE_API_KEYS or GROQ_API_KEY)


def auth_enabled() -> bool:
    """True when Supabase JWT verification is configured."""
    return bool(SUPABASE_JWT_SECRET)


def billing_enabled() -> bool:
    """True when Stripe is configured; gates checkout and tier enforcement."""
    return bool(STRIPE_SECRET_KEY)
