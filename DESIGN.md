# Praxis — Design & Architecture

**Praxis — a governed multi-agent document intelligence workspace.**

Upload a corpus of mixed documents and a coordinated team of agents lets you query,
cross-reference, compare, and extract insights across the *whole* corpus — with
permissions, an audit trail, and a grounding check on every answer.

> Success in one sentence: *"Upload 15 mixed documents, ask 'which of these contradict
> each other on payment terms?', and watch a team of agents fan out across all 15 in
> parallel, cross-reference them, flag the conflicts with citations to each source page,
> and show an audit trail of exactly what was accessed."*

This is the 4th portfolio project. It must show what the others don't:
DocChat = single-doc RAG, Scout = linear self-correcting research agent,
Atlas = multi-agent SQL analyst. **Praxis = the production-safe agent layer:
orchestration + governance + cross-document reasoning at scale.**

Neutral demo domain: **commercial contracts / vendor agreements / company policies /
product manuals / HR docs.** (Deliberately NOT SEC / legal-citation / financial-regulatory.)

---

## 1. Capability coverage matrix (proves nothing in the brief is dropped)

| # | Required capability | How Praxis delivers it | Phase |
|---|---|---|---|
| A | Multi-agent harness (orchestrator + sub-agents) | LangGraph stateful graph: Router → Retriever → Cross-Doc Reasoner / Conflict Detector / Extractor → Synthesizer → Verifier | M3 |
| A2 | Conversation memory (multi-turn, pronoun resolution, context mgmt) | Per-session history object + working-set tracker + rolling-summary compression, persisted in Postgres (LangGraph checkpointer) | M4 |
| B | Adaptive retrieval (strategy per query) | Router classifies intent+complexity → lightweight / multi-step / graph / hierarchical; surfaced in glass-box | M2, M5 |
| C | Multi-document at scale | Hierarchical retrieval (doc-summary routing → chunk), 10–50+ docs incl. large files | M2 |
| D | Multimodal ingestion | PyMuPDF (text/images) + pdfplumber (tables) + Tesseract OCR (scanned) + python-docx (Word); Gemini-vision upgrade path | M1 |
| E | Governance & trust | Role-based doc access + role switcher, full audit log, grounding/hallucination check, glass-box trace | M7 |
| F | Cross-document intelligence | Compare / extract-across-corpus / **contradiction detection** with per-source citations | M6 |
| G | Unique professional UI | Custom "Praxis" design system, 3-panel workspace, live animated agent pipeline, interactive citations, contradiction view, role switcher, dark/light, responsive | M9 |
| Opt | Explain-your-confidence | Grounding verdict + reasoning per answer | M7 |
| Opt | Permission simulation | Role switcher flips accessible docs + answers live | M7 |
| Opt | Live web augmentation | Tavily fallback when corpus can't answer (clearly labeled) | M10 |
| Opt | Export | Sourced Markdown / PDF report of an analysis | M10 |
| — | Subscriptions (Free / Pro / Enterprise) | Supabase Auth + Stripe Checkout (test mode) + tier gating | M8 |

**All required + all optional features are in scope.**

---

## 2. Stack decisions

| Layer | Choice | Why |
|---|---|---|
| Agent harness | **LangGraph** (Python) | Stateful graph, checkpointing, conditional routing, HITL — proven in Atlas; the cleanest fit for orchestration |
| LLM abstraction | **LangChain** chat/embeddings + `.with_fallbacks()` | Provider-agnostic; one-line swap to another provider (e.g. OpenAI) |
| LLM providers | **Multi-key Gemini → Groq** fallback (established pattern) | `GOOGLE_API_KEYS` (rotated) gemini-2.5-flash → flash-lite, then `GROQ_API_KEY` llama-3.3-70b. Free. |
| Embeddings | **gemini-embedding-001** (768-dim, key rotation) | Free; matches DocChat/Atlas |
| Reranker | **Local cross-encoder** `ms-marco-MiniLM-L-6-v2` (CPU) | Zero API cost; runs in the HF container |
| API | **FastAPI + SSE** | Streaming glass-box pipeline; matches Scout/Atlas |
| Vector + keyword + data | **Supabase Postgres + pgvector + FTS** | One backbone for vectors (semantic), `tsvector` (keyword), audit, roles, subscriptions |
| Auth | **Supabase Auth** | Consolidates with the DB; free; email + OAuth |
| File storage | **Supabase Storage** | Keep originals for citation highlighting; 1GB free |
| Ingestion | PyMuPDF, pdfplumber, python-docx/mammoth, pytesseract+Pillow | Free, covers text/tables/Word/scanned |
| Payments | **Stripe Checkout + Customer Portal (TEST mode)** | Test mode is free; full flow with test cards; live mode = config flip. (Lemon Squeezy = simpler MoR alternative) |
| Frontend | **Next.js 15 + TypeScript + Tailwind + Framer Motion** | Flagship UI with custom design system + live pipeline animation |
| Backend host | **Hugging Face Spaces (Docker)** | Free, 16GB RAM, fits reranker model; matches Scout/Atlas |
| Frontend host | **Vercel** | Free, CDN, matches DocChat |
| Keep-warm | **GitHub Actions cron → /health** | Free; mitigates HF sleep |

**Net cost of the public demo: $0** (see §11).

---

## 3. System architecture

```
                         ┌───────────────────────────────────────────────┐
                         │  FRONTEND  (Next.js / Vercel)                  │
                         │  3-panel workspace:                            │
                         │  Documents │ Conversation │ Glass-box Inspector│
                         │  live agent pipeline · role switcher · billing │
                         └───────────────┬───────────────────────────────┘
                                         │ REST + SSE (token & event stream)
                         ┌───────────────▼───────────────────────────────┐
                         │  BACKEND  (FastAPI / HF Spaces, Docker)        │
                         │                                                │
                         │  ┌── Ingestion pipeline ──────────────────┐    │
                         │  │ parse(PDF/Word/txt) → tables → OCR →    │    │
                         │  │ chunk → embed(cached) → index           │    │
                         │  └─────────────────────────────────────────┘    │
                         │                                                │
                         │  ┌── Agent harness (LangGraph) ───────────┐    │
                         │  │ memory/resolve → ROUTER → retriever →   │    │
                         │  │ {cross-doc | conflict | extract} →      │    │
                         │  │ synthesizer → VERIFIER → memory-update  │    │
                         │  └─────────────────────────────────────────┘    │
                         │                                                │
                         │  Retrieval: pgvector + FTS → RRF → rerank      │
                         │  Governance: roles · audit · grounding         │
                         │  Caching: embed · query · context · sample     │
                         │  Billing: Stripe webhooks → tier gating        │
                         └───────────────┬───────────────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        │                                │                                 │
┌───────▼────────┐          ┌────────────▼───────────┐        ┌────────────▼────────┐
│ Supabase       │          │ Gemini (multi-key) →   │        │ Stripe (test) ·     │
│ Postgres+pgvec │          │ Groq fallback ·        │        │ Tavily (web aug) ·  │
│ Auth · Storage │          │ gemini-embedding-001   │        │ GH Actions keepwarm │
└────────────────┘          └────────────────────────┘        └─────────────────────┘
```

---

## 4. Data model

> **Storage is pluggable (refinement).** A `Store` interface has two
> implementations: **`local`** — SQLite (FTS5 keyword) + NumPy cosine vectors +
> local files, runs the whole app with zero external infra (dev + free demo) — and
> **`supabase`/Postgres + pgvector** for production. Same schema below; switching is
> a `STORE_BACKEND` env flag. Reranking is RRF by default (no heavy deps) with an
> optional cross-encoder/LLM rerank upgrade.

The schema (Postgres form; the local backend mirrors it in SQLite):

```
users                (Supabase Auth)
subscriptions        user_id, tier[free|pro|enterprise], stripe_customer_id,
                     stripe_subscription_id, status, current_period_end
documents            id, owner_id, filename, mime, size, page_count, status
                     [queued|parsing|ocr|embedding|ready|failed], file_hash,
                     storage_path, summary, created_at
document_roles       document_id, role            -- e.g. 'legal','finance','hr','public'
document_chunks      id, document_id, page, ordinal, kind[text|table|ocr],
                     content, embedding vector(768), fts tsvector, token_count
doc_entities         document_id, entity_type[party|date|amount|term|obligation],
                     value, chunk_id           -- powers graph-style retrieval
conversations        id, owner_id, title, active_role, summary, working_set jsonb,
                     created_at
messages             id, conversation_id, role[user|assistant], content,
                     strategy, grounding_verdict, confidence, created_at
message_sources      message_id, chunk_id, document_id, page, snippet, rank
audit_log            id, conversation_id, message_id, actor[agent name], action
                     [retrieve|read|compare|verify|web], target, role_context, ts
query_cache          key(hash of normalized_query+corpus_hash+role), answer jsonb,
                     sources jsonb, created_at, ttl
embedding_cache      content_hash, embedding vector(768)
```

Indexes: `ivfflat`/`hnsw` on `document_chunks.embedding`, GIN on `document_chunks.fts`,
btree on role/owner. Row-level security ties documents/conversations to `owner_id`.

---

## 5. Ingestion pipeline (multimodal)

1. **Upload** (multipart) → store original in Supabase Storage, compute `file_hash`
   (idempotency: identical file = skip re-processing).
2. **Parse by type:** PDF → PyMuPDF; Word → python-docx/mammoth; txt → direct.
3. **Tables:** pdfplumber/PyMuPDF table extraction → serialized as Markdown tables
   (kept as `kind='table'` chunks so the LLM reads them faithfully).
4. **Scanned/image pages:** detect low text-density pages → Tesseract OCR
   (`kind='ocr'`); low-confidence pages → optional Gemini-vision upgrade.
5. **Chunk:** structure-aware (headings/sections) with overlap; tables/figures kept whole.
6. **Embed:** gemini-embedding-001 (768) with **embedding cache** (content hash) + key rotation.
7. **Index:** write chunks (embedding + `tsvector`) + extract `doc_entities` + a per-doc
   `summary` (one cheap call, cached) used for hierarchical routing.
8. **Status streamed** to the UI (queued→parsing→ocr→embedding→ready).

---

## 6. Retrieval (hybrid · hierarchical · adaptive)

**Baseline quality bar (every query):** hybrid = pgvector semantic + Postgres FTS keyword,
fused with **Reciprocal Rank Fusion**, then **cross-encoder rerank** of the top candidates.
All retrieval is **role-filtered** (governance) before anything reaches an agent.

**Adaptive strategy (router picks one + says why):**
- **Lightweight** — simple factual lookup: single hybrid pass, small K.
- **Multi-step** — cross-doc / multi-hop: decompose into sub-questions, retrieve per
  sub-question, merge.
- **Graph-style** — "how do these connect": traverse `doc_entities`
  (shared parties/terms/dates) to pull linked passages across docs.
- **Hierarchical** — large/many-doc corpus: route on per-doc summaries first to pick
  candidate docs, then retrieve chunks within them (keeps cost/context bounded).

---

## 7. Agent harness (LangGraph)

**State**
```
messages[]            full turn history (compacted by summary)
working_set[]         doc ids currently "in focus" (for pronoun resolution)
active_role           governance context
query, resolved_query reference-resolved question
intent                lookup | crossdoc | compare | contradiction | extract
strategy              chosen retrieval strategy (+ reason)
retrieved[]           role-filtered, reranked chunks
analysis              cross-doc / conflict / extraction result
draft                 synthesized answer + citations
grounding             verdict, confidence, unsupported_claims[]
audit[]               every retrieval/agent action
summary, entities     compressed memory
```

**Graph**
```
memory_load → resolve_references → ROUTER ─┬─► retriever ─► synthesizer ─► VERIFIER ─► memory_update
                                           │                                  │
              (intent conditionals)        ├─► cross_doc_reasoner ────────────┤
                                           ├─► conflict_detector ─────────────┤   (if ungrounded:
                                           └─► extractor ─────────────────────┘    revise ↺ once,
                                                                                    then honest "no evidence")
```
- **Orchestrator** = the graph + router's conditional edges.
- **Verifier** gates output: re-checks every claim against cited chunks; one bounded
  revise loop; otherwise returns an honest "the documents don't support this."
- Each node emits an **SSE event** so the UI animates the live pipeline.

---

## 8. Conversation memory (first-class)

- **History object** per session: ordered user/assistant turns + which docs/sources each
  answer used. The relevant slice is fed to the LLM **every** turn.
- **Reference resolution:** a cheap structured step resolves "those / them / the second one /
  it" against `working_set` + history before retrieval.
- **Context management:** rolling-summary compression — older turns compress into a running
  summary while preserving entities + current working set, so long sessions never exceed the
  window (and cost stays flat).
- **Persistence:** LangGraph Postgres checkpointer → survives turns and page refresh within a session.
- **Governance-aware:** memory never carries content from docs the active role can't see.
- **Two separate memories:** dialogue memory (this) vs corpus/retrieval memory (vectors).

---

## 9. Governance & trust (the differentiator)

- **Permissions:** documents tagged with roles; retrieval filtered by `active_role`.
  UI **role switcher** flips the view → accessible docs + answers change live.
- **Audit log:** every retrieve/read/compare/verify/web action recorded
  (actor agent, target doc/page, role context, timestamp) and viewable in the inspector.
- **Grounding check:** verifier confirms support before display; unsupported → honest refusal.
- **Glass-box trace:** inspector shows chosen strategy + reason, retrieved chunks, agents that
  acted, grounding verdict + confidence, and the audit entries for that answer.

---

## 10. Cross-document intelligence & contradiction detection (the "wow")

Contradiction algorithm:
1. Identify the topic (from the query, or a target statement).
2. Cross-doc retrieve top passages **per document** on that topic (one bucket per doc).
3. Extract each doc's **stance/value** as structured data `{doc, stance, quote, page}`.
4. LLM compares stances → `agree | conflict | unrelated` + rationale + citations
   (self-consistency only here, where it matters).
5. **Side-by-side conflict view** in the UI with the disagreeing clauses highlighted.

Cached per `(corpus_hash, topic)` so re-asking is instant and free.
Also supports "compare X across these" and "extract all dates/parties/obligations."

---

## 11. Caching & cost efficiency (explicit)

| Layer | Mechanism | Saves |
|---|---|---|
| Embedding cache | content-hash → reuse embedding; dedupe identical chunks | embedding calls |
| Ingestion idempotency | file-hash → skip re-processing same upload | full re-ingest |
| Semantic query cache | (normalized query + corpus_hash + role) → answer+sources | whole pipeline on repeats |
| Router cache | identical query → cached strategy/intent | a classify call |
| Provider context cache | stable prompt prefixes (+ Gemini context cache where available) | input tokens on same-corpus queries |
| Local reranker | CPU cross-encoder, no API | rerank API cost |
| Pre-warmed sample corpus | ship sample docs pre-embedded + pre-cached | ~0 cost + instant public demo |
| Summary compression | cap conversation tokens | tokens on long sessions |
| Adaptive routing | simple queries → one cheap call (skip multi-agent) | unnecessary agent calls |

**Prompt engineering:** minimal instruction-first per-agent system prompts; structured
(Pydantic/JSON) outputs for router/extractor/conflict/verifier (deterministic, fewer tokens);
strict grounding + citation format; low temp for routing/verification, moderate for synthesis;
stable cache-friendly prefixes; few-shot only where it changes behavior.

---

## 12. Subscriptions & payments

| Tier | Docs / size | Queries/day | Strategies | Governance | Extras |
|---|---|---|---|---|---|
| **Free** | ≤5 / 10MB + sample corpus | 15 | lightweight + multi-step | single role, audit view | — |
| **Pro** | ≤50 / 50MB | 300 | all incl. graph + hierarchical | all roles + switcher | export, web augmentation, priority |
| **Enterprise** | ≤500 | high | all | custom roles, API access | dedicated keep-warm, SSO note |

- **Public demo needs no login** to try the pre-loaded sample corpus (brief requirement).
- **Stripe Checkout (subscription mode) + Customer Portal**, TEST mode (free, test cards).
  Webhooks (`checkout.session.completed`, `customer.subscription.updated|deleted`) → update
  `subscriptions`. Backend middleware gates actions by tier with friendly upgrade prompts.
- Live mode = swapping keys + flipping a flag. Documented in README.

---

## 13. API surface

**REST:** `POST /documents` (upload) · `GET /documents` · `DELETE /documents/:id` ·
`POST /documents/:id/roles` · `POST /conversations` · `GET /conversations/:id` ·
`POST /conversations/:id/messages` (→ SSE) · `GET /audit` · `GET /trace/:messageId` ·
`POST /billing/checkout` · `POST /billing/portal` · `POST /billing/webhook` ·
`POST /sample/load` (no auth) · `GET /health`.

**SSE events (glass-box live pipeline):** `agent_step{agent,status}` ·
`strategy_selected{strategy,reason}` · `retrieval{chunks[]}` · `token{delta}` ·
`citation{id,doc,page,passage}` · `grounding{verdict,confidence,unsupported[]}` ·
`conflict{pairs[]}` · `audit{entries[]}` · `done` · `error{friendly_message}`.

---

## 14. Frontend — design system & UX

**Identity (distinct from cyan/violet/pink siblings):** "Praxis" = governed intelligence.
Proposed: **slate canvas + emerald "verified/trust" accent + amber/red "conflict" accent**
(green = grounded, amber/red = contradiction — the colors *mean* something). Refined geometric
sans (e.g. Geist / Space Grotesk headings), considered spacing, subtle glass panels,
purposeful micro-interactions. Premium, trustworthy — not default Tailwind.

**Layout — 3-panel workspace:**
- **Documents panel** — corpus list with type icons, page counts, status, per-doc role tags, dropzone, "Load sample corpus."
- **Conversation panel** — threaded multi-turn history (clearly visible/scrollable), streamed answers, inline citation chips, follow-up aware.
- **Inspector (glass-box)** — tabs: Pipeline · Retrieval · Grounding · Audit.

**Signature components:** animated **AgentPipeline** (orchestrator → sub-agents → verifier,
live via SSE, Framer Motion — never a frozen spinner) · **CitationPopover** (click → source doc
+ page + highlighted passage) · **ContradictionView** (side-by-side, highlighted conflicting
clauses, severity) · **RoleSwitcher** (segmented "view as…") · **ConfidenceBadge** (verdict +
reasoning) · pricing/billing page · dark/light toggle · responsive.

---

## 15. Sample dataset (ships in repo, pre-indexed)

~12–15 mixed neutral-domain docs (vendor agreements, SOWs, policies, manuals, NDAs, SLAs, HR
handbook) including a couple of **scanned-image PDFs** and a couple with **pricing tables**, with
**baked-in contradictions**:
- Payment terms: Net-30 vs Net-45 vs Net-60
- Termination notice: 30 vs 60 vs 90 days
- Data retention: 90 days vs 1 year vs "indefinite"
- Warranty period + liability-cap mismatches

Pre-embedded + pre-cached so the contradiction demo runs instantly at $0 with no upload.

---

## 16. Deployment & ops

- **Backend:** HF Spaces Docker, FastAPI on `:7860`. Secrets: `GOOGLE_API_KEYS`,
  `GROQ_API_KEY`, `TAVILY_API_KEY`, `SUPABASE_URL/SERVICE_KEY`, `STRIPE_SECRET/WEBHOOK`.
- **Frontend:** Vercel. Env: `NEXT_PUBLIC_API_URL`, Supabase anon key, Stripe publishable key.
- **Data/Auth/Storage:** Supabase project.
- **Keep-warm:** GitHub Actions cron pings `/health`; UI shows a friendly "warming up" state
  on cold start (~30–60s) instead of a frozen screen.
- **Provider-agnostic:** LLM layer mirrors Atlas — switching to another provider (e.g. OpenAI) is config-only.

---

## 17. Repo structure

```
praxis/
  backend/
    app/
      main.py  config.py  llm.py  db.py  schemas.py
      ingest/      parse.py  tables.py  ocr.py  chunk.py  embed.py
      retrieval/   hybrid.py  rerank.py  hierarchical.py  graph.py
      agents/      graph.py  nodes.py  prompts.py  memory.py
      governance/  roles.py  audit.py  grounding.py
      billing/     stripe.py  tiers.py
      cache/       cache.py
    Dockerfile  .dockerignore  requirements.txt
  frontend/        (Next.js app/, components/, lib/, styles/)
  sample-data/     (docs + seed script)
  docs/            (architecture diagram + screenshots)
  .github/workflows/keepalive.yml
  README.md
```

---

## 18. Build milestones (each shippable)

- **M0** Scaffold + infra (Supabase/HF/Vercel) + LLM fallback layer + health/keep-warm
- **M1** Multimodal ingestion → chunk → embed(cached) → index + sample corpus seeded
- **M2** Hybrid + hierarchical retrieval + local reranker (per-doc & cross-doc)
- **M3** Agent harness (router→retriever→synth→verifier) + SSE glass-box events
- **M4** Conversation memory (history, reference resolution, summary compression, persistence)
- **M5** Adaptive routing (strategy-per-query) + glass-box strategy display
- **M6** Cross-doc intelligence + **contradiction detection**
- **M7** Governance (roles, role switcher, audit, grounding verdicts) + confidence explainer
- **M8** Auth (Supabase) + subscriptions (Stripe test) + tier gating
- **M9** Premium UI (design system, workspace, animated pipeline, citations, contradiction view, dark/light, responsive)
- **M10** Caching/cost hardening + prompt tuning + graceful failure + web augmentation + export
- **M11** Sample-data polish + README (diagram, screenshots, skills, provider note) + deploy + QA

Scope discipline: each layer works before the next; small corpus that works perfectly beats a
huge one that breaks. The three flagship anchors: **harness + contradiction detection + governance.**

---

## 19. Cost model

**Public demo = $0.** Gemini/Groq free tiers (multi-key), gemini embeddings free, local
reranker, Supabase free (DB+Auth+Storage), HF Spaces free, Vercel free, Stripe test mode free,
Tesseract free, GitHub Actions free.

**If you ever want to remove cold starts / raise limits (optional, cheapest first):**
1. Free GitHub Actions keep-warm (already planned) — usually enough.
2. Gemini pay-as-you-go — Flash is pennies per 1M tokens; effectively the cheapest accuracy upgrade.
3. ~$5–7/mo always-on backend (Render/Railway) only if HF cold starts annoy you.
4. Cohere/Jina rerank (free tiers exist; paid is cheap) only if you want best-in-class reranking.

Accuracy is protected regardless: hybrid retrieval + reranking + grounding verifier +
contradiction self-consistency do the heavy lifting, independent of which provider serves tokens.

---

## 20. Risks & mitigations

- Free-tier rate limits → multi-key fallback + caching + friendly messages.
- HF cold start → keep-warm + warming UI.
- Supabase 500MB / large docs → hierarchical retrieval + store summaries; free-tier upload caps; swappable to Neon.
- OCR quality → Tesseract + optional Gemini-vision fallback.
- Reranker image weight → small MiniLM; skip rerank on Free tier if needed.
- Stripe complexity → test mode + minimal webhook set.
- Scope creep → phased milestones, each shippable; locked small sample corpus.

---

## 21. Locked decisions

1. **Deployment topology** — **split: Next.js on Vercel + FastAPI on Hugging Face Spaces (Docker).**
2. **Auth + payments** — **Supabase Auth + Stripe Checkout (test mode), live mode = config flip.**
3. **Visual identity / accent** — **slate canvas + emerald "verified/trust" accent + amber/red "conflict" accent.**
```
