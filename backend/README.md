---
title: Praxis
emoji: 🧭
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: Governed multi-agent document intelligence API
---

# Praxis — Backend API

FastAPI service powering **Praxis**, a governed multi-agent document intelligence
workspace: multimodal ingestion, hybrid retrieval, a LangGraph agent harness,
cross-document contradiction detection, grounding checks, role-based governance,
and an audit trail.

- Health check: `/health`
- API docs: `/docs`

Source and full documentation: https://github.com/Roshaan-Ullah-Zaheer/praxis

## Configuration

Set these as Space **Settings → Variables and secrets**:

| Secret | Required | Purpose |
|---|---|---|
| `GOOGLE_API_KEYS` | yes | Comma-separated Gemini API keys (rotated) |
| `GROQ_API_KEY` | optional | Fallback LLM provider |
| `TAVILY_API_KEY` | optional | Opt-in web-augmentation fallback |
| `CORS_ORIGINS` | yes | Your Vercel frontend URL (comma-separated) |

Billing and auth (`STRIPE_*`, `SUPABASE_*`) are optional — the demo runs without them.
