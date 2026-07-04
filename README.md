# Praxis

**A governed multi-agent document intelligence workspace.**

Upload a corpus of mixed documents and a coordinated team of agents lets you query,
cross-reference, compare, and find contradictions across the *whole* corpus — every answer
carries citations, a grounding check, role-based permissions, and a full audit trail.

> Upload 15 mixed documents, ask *"which of these contradict each other on payment terms?"*,
> and watch a team of agents fan out across all 15 in parallel, cross-reference them, flag the
> conflicts with citations to each source page, and show an audit trail of exactly what was accessed.

Neutral demo domain: commercial contracts, vendor agreements, company policies, product
manuals, and HR documents.

---

## Why it exists

Most "chat with your docs" demos stop at single-document retrieval. Praxis is the
**production-safe agent layer**: orchestration, governance, and cross-document reasoning at
scale. The three things it is built to prove:

1. **Multi-agent harness** — a LangGraph orchestrator routes each question to the right
   sub-agents (retriever, conflict detector, synthesizer) and a verifier gates every answer.
2. **Contradiction detection** — fan out across the corpus, extract each document's stance on a
   topic, and surface the disagreements side by side with citations.
3. **Governance & trust** — role-based document access, a grounding/hallucination check on every
   answer, and a complete audit log — all visible in a glass-box inspector.

---

## Features

- **Multimodal ingestion** — PDF (PyMuPDF), Word (python-docx), plain text; table extraction
  (pdfplumber) and OCR fallback (Tesseract) for scanned pages. Idempotent on file content and
  status-tracked end to end.
- **Hybrid retrieval** — semantic (vector) + keyword (full-text) search fused with Reciprocal
  Rank Fusion, role-filtered before anything reaches an agent.
- **Adaptive routing** — a router classifies each query's intent and picks a retrieval strategy
  (lightweight / multi-step / graph / hierarchical), and tells you why.
- **Cross-document intelligence** — compare a clause across documents, extract entities across
  the corpus, and detect contradictions with per-source citations.
- **Conversation memory** — multi-turn dialogue with reference resolution ("the second one",
  "those") and rolling-summary compression so long sessions stay cheap.
- **Grounding verifier** — re-checks every claim against its cited passages; one bounded revision
  on weak grounding, otherwise an honest "the documents don't support this."
- **Glass-box inspector** — live agent pipeline, retrieved passages, grounding verdict +
  confidence, and the audit trail for every answer.
- **Caching** — embedding cache, ingestion idempotency, and a semantic query cache that replays
  grounded answers instantly with zero LLM calls.
- **Sourced export** — download any analysis as a cited Markdown report.

---

## Architecture

```
Frontend (Next.js / Vercel)
  3-panel workspace: Documents | Conversation | Glass-box Inspector
  live agent pipeline · interactive citations · contradiction view · role switcher
        │  REST + SSE (event stream)
Backend (FastAPI / Hugging Face Spaces, Docker)
  Ingestion:  parse → tables → OCR → chunk → embed (cached) → index
  Agents:     memory → router → {retriever | conflict detector | extractor}
                     → synthesizer → verifier
  Retrieval:  vector + keyword → RRF
  Governance: roles · audit · grounding
        │
  Store (pluggable): local SQLite (FTS5) + NumPy vectors  ·OR·  Postgres + pgvector
  LLM: multi-key Gemini → Groq fallback · gemini-embedding-001
```

### Pluggable storage
A single `Store` interface has two implementations selected by `STORE_BACKEND`:

- **`local`** (default) — SQLite with FTS5 keyword search + NumPy cosine vectors + local files.
  Runs the whole app with zero external infrastructure.
- **`supabase`** — Postgres + pgvector + Supabase Auth/Storage for production.

---

## Tech stack

| Layer | Choice |
|---|---|
| Agent harness | LangGraph (stateful graph, conditional routing, bounded revision loop) |
| LLM | Multi-key Gemini (`gemini-2.5-flash` → `flash-lite`) → Groq (`llama-3.3-70b`) fallback |
| Embeddings | `gemini-embedding-001` (768-dim) with content-hash cache |
| API | FastAPI + Server-Sent Events |
| Storage | SQLite + FTS5 (local) / Postgres + pgvector (prod) |
| Frontend | Next.js 15, TypeScript, Tailwind CSS, Framer Motion |
| Ingestion | PyMuPDF, pdfplumber, python-docx, Tesseract |

The LLM layer is provider-agnostic — switching to another provider (e.g. OpenAI) is a
configuration change.

---

## Local development

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate           # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
cp .env.example .env             # add GOOGLE_API_KEYS (and optionally GROQ_API_KEY)
python -m uvicorn app.main:app --port 7860 --reload
```

API docs at `http://localhost:7860/docs`, health check at `/health`.

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:7860
npm run dev
```

Workspace at `http://localhost:3000`.

### Smoke tests

The backend ships runnable smoke scripts that exercise each layer end to end:

```bash
cd backend
.venv/Scripts/python scripts/smoke_ingest.py     # ingest → index → hybrid search → role filter
.venv/Scripts/python scripts/smoke_agent.py      # router → retrieve → synthesize → verify
.venv/Scripts/python scripts/smoke_chat.py        # multi-turn memory + reference resolution
.venv/Scripts/python scripts/smoke_conflict.py    # contradiction detection across documents
.venv/Scripts/python scripts/smoke_cache.py       # query cache replay
```

---

## Project structure

```
praxis/
  backend/
    app/
      main.py  config.py  llm.py  schemas.py
      ingest/      parse · tables · ocr · chunk · embed · pipeline
      retrieval/   hybrid (vector + keyword + RRF)
      agents/      graph · nodes · runner (SSE) · memory · prompts · state
      api/         documents · conversations · governance
      store/       base (interface) · local (SQLite + NumPy)
      cache/       query_cache
    scripts/       smoke tests
    Dockerfile  requirements.txt
  frontend/
    app/           layout · page · pricing · globals.css
    components/    Workspace · DocumentsPanel · ConversationPanel · Inspector
                   AgentPipeline · ContradictionView · CitationChip · RoleSwitcher · …
    lib/           api · types · useConversation · markdown
  DESIGN.md        full design & architecture
```

---

## Status

| Area | State |
|---|---|
| Ingestion, retrieval, agent harness, memory, routing | Complete |
| Contradiction detection, governance, grounding, caching | Complete |
| Premium 3-panel workspace UI (dark/light) | Complete |
| Token-by-token streaming · sourced export | Complete |
| Sample corpus + one-click loader | Complete |
| Web augmentation (opt-in fallback) | Complete |
| Auth + subscriptions (Supabase + Stripe) | Config-gated — add keys to enable |

See [`DESIGN.md`](./DESIGN.md) for the full architecture, data model, and milestone plan.

---

## Configuration

All backend settings are environment variables (see [`backend/.env.example`](./backend/.env.example)).
The app runs on free defaults; optional services are off until their keys are set.

| Variable | Purpose |
|---|---|
| `GOOGLE_API_KEYS` | Comma-separated Gemini keys (rotated). Required. |
| `GROQ_API_KEY` | Fallback LLM provider. Optional. |
| `STORE_BACKEND` | `local` (SQLite, default) or `supabase` (Postgres + pgvector). |
| `TAVILY_API_KEY` | Enables the opt-in web-augmentation fallback. Optional. |
| `SUPABASE_JWT_SECRET` | Enables auth; without it the app runs no-login demo mode. |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | Enable subscriptions + tier limits. Without them the demo is unlimited. |
| `STRIPE_PRICE_PRO` / `STRIPE_PRICE_ENTERPRISE` | Stripe price IDs for checkout. |
| `FRONTEND_URL` | Where Stripe Checkout returns the user. |
| `CORS_ORIGINS` | Allowed frontend origins. |

The frontend needs only `NEXT_PUBLIC_API_URL` (see [`frontend/.env.local.example`](./frontend/.env.local.example)).

---

## Deployment

- **Backend → Hugging Face Spaces (Docker).** The included [`backend/Dockerfile`](./backend/Dockerfile)
  installs Tesseract + Poppler and serves FastAPI on `:7860`. Add the environment variables as
  Space secrets. The bundled sample corpus ships in the image.
- **Frontend → Vercel.** Set `NEXT_PUBLIC_API_URL` to the Space URL.
- **Data / Auth / Storage → Supabase** (when `STORE_BACKEND=supabase`).
- **Payments → Stripe** (test mode is free; live mode is a key swap).
- **Keep-warm.** [`.github/workflows/keepalive.yml`](./.github/workflows/keepalive.yml) pings
  `/health` every 20 minutes so the free Space doesn't sleep — update the URL after deploy.

---

## Cost

The public demo is designed to run entirely on free tiers — Gemini/Groq free keys, free
embeddings, a local reranker, SQLite (or Supabase free tier), Hugging Face Spaces, and Vercel.
