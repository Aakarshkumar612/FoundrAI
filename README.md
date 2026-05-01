# FoundrAI — Autonomous AI Advisory Platform for Startup Founders

FoundrAI gives startup founders a private AI analyst. Upload your financial CSVs, ask natural-language questions, run scenario simulations, and get structured answers backed by your own data, live market news, and four specialist AI agents — all streamed in real time.

---

## What It Does — The User Journey

1. **Register / Login** — Supabase auth creates a JWT-secured session. Email + password with optional TOTP MFA.
2. **Upload financials** — CSV, Excel, PDF, or plain text. The backend extracts text, chunks it, embeds it into pgvector, and parses financial columns (revenue, burn, CAC, LTV) into a structured metrics snapshot.
3. **Ask a question** — e.g. *"What is my runway if CAC increases by 20% next quarter?"*. Four AI agents answer in sequence, each reading the previous agent's output and the founder's retrieved document chunks.
4. **Run a simulation** — Choose bear / base / bull, set CAC and burn sliders, pick a forecast horizon. 10,000 Monte Carlo paths run in ~100ms and return P10/P50/P90 revenue bands with runway estimates.
5. **View charts** — Recharts-powered area charts with confidence band fills and animated tooltips.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend API | FastAPI + Uvicorn (Python 3.12) | Async-native, automatic OpenAPI docs, type-safe schemas |
| AI Agents | Groq API — Llama 3.1-8b-instant + Llama 3.3-70b | ~500 tok/sec, free tier, structured JSON output |
| RAG | pgvector (Supabase) + sentence-transformers | Semantic search over founder's own documents |
| News | NewsCatcher API + News-Please + APScheduler | Scheduled ingestion, deduplication, full-text extraction |
| Simulation | NumPy vectorised Monte Carlo (10K paths) | Pure-Python, no GPU needed, runs in < 200ms |
| Auth | Supabase Auth + PyJWT middleware | Managed JWTs, RLS, TOTP MFA out of the box |
| Database | Supabase PostgreSQL 15 + pgvector extension | One hosted DB with vector search, RLS, and real-time |
| File Storage | Supabase Storage | Durable raw upload storage, bucket-based |
| Frontend | React 18 + Vite + TailwindCSS + Framer Motion | Fast HMR, component-level animations |
| Charts | Recharts | Composable SVG charts with custom tooltips |
| Deployment | Render (Backend) + Vercel (Frontend) | Automated CI/CD from GitHub |
| Config | pydantic-settings | Type-validated env vars with `.env` file support |

---

## Repository Structure

```
FoundrAI/
│
├── backend/
│   ├── main.py                         # FastAPI app, CORS, lifespan, routers
│   ├── config.py                       # pydantic-settings: all env vars, typed
│   │
│   ├── auth/
│   │   ├── router.py                   # POST /auth/register, /login, /refresh, /logout, MFA, GET /me
│   │   ├── middleware.py               # verify_jwt dependency — validates Supabase JWTs on every request
│   │   └── schemas.py                  # Pydantic request/response models for auth
│   │
│   ├── agents/
│   │   ├── orchestrator.py             # Sequential 4-agent pipeline, SSE event emitter
│   │   ├── market_agent.py             # Llama 3.1-8b — TAM/SAM/SOM, competitors, opportunities
│   │   ├── risk_agent.py               # Llama 3.1-8b — financial and market risk assessment
│   │   ├── revenue_agent.py            # Llama 3.1-8b — revenue analysis and growth projections
│   │   └── strategy_agent.py           # Llama 3.3-70b — final strategic recommendations
│   │
│   ├── rag/
│   │   ├── pipeline.py                 # RAGPipeline class: unified index + query interface
│   │   ├── indexer.py                  # Chunk documents, embed, store in pgvector
│   │   ├── encoder.py                  # sentence-transformers embedding wrapper
│   │   └── retriever.py                # pgvector cosine similarity search
│   │
│   ├── automl/
│   │   └── monte_carlo.py              # Vectorised 10K-path Monte Carlo, P10/P50/P90 bands
│   │
│   ├── news/
│   │   ├── ingestion.py                # NewsCatcher fetch + News-Please full-text + RAG index
│   │   └── scheduler.py                # APScheduler job: ingest_news_batch every 6 hours
│   │
│   ├── storage/
│   │   ├── supabase_client.py          # Singleton Supabase client (service role)
│   │   ├── supabase_storage.py         # Upload/download helpers for the uploads table
│   │   └── extractors.py               # CSV/Excel/PDF/image → text + structured metrics extraction
│   │
│   ├── routers/
│   │   ├── upload.py                   # POST /upload/financials — multipart file upload
│   │   ├── query.py                    # POST /query — SSE stream of agent events
│   │   ├── simulate.py                 # POST /simulate — Monte Carlo result
│   │   ├── charts.py                   # GET /charts — historical simulation data
│   │   └── founders.py                 # GET/PATCH /founders/me — founder profile CRUD
│   │
│   ├── tests/
│   │   ├── test_auth.py
│   │   ├── test_agents.py
│   │   ├── test_rag.py
│   │   ├── test_news.py
│   │   ├── test_extractors.py
│   │   ├── test_api.py
│   │   ├── test_storage.py
│   │   └── test_integration.py
│   │
│   └── storage/migrations/
│       ├── 001_create_founders.sql
│       ├── 002_create_document_embeddings.sql
│       ├── 003_create_news_tables.sql
│       ├── 004_create_uploads.sql
│       ├── 004b_add_metrics_column.sql
│       └── 005_create_simulation_results.sql
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx                    # React entry point, QueryClient, BrowserRouter
│   │   ├── App.tsx                     # Route tree: public + ProtectedRoute-gated app routes
│   │   │
│   │   ├── shared/
│   │   │   ├── auth/supabase.ts        # Supabase browser client (anon key)
│   │   │   ├── api/client.ts           # Typed API client (GET/POST/upload + SSE streamQuery)
│   │   │   ├── types.ts                # Shared TypeScript interfaces
│   │   │   ├── components/Layout.tsx   # Sidebar + Outlet wrapper for app routes
│   │   │   ├── components/ProtectedRoute.tsx  # Redirects unauthenticated users to /auth/login
│   │   │   └── components/Spinner.tsx  # Animated loading indicator
│   │   │
│   │   └── features/
│   │       ├── landing/LandingPage.tsx # Public marketing page — hero, features, CTA
│   │       ├── auth/LoginPage.tsx      # Email/password login form → POST /auth/login
│   │       ├── auth/RegisterPage.tsx   # Registration form → POST /auth/register
│   │       ├── dashboard/DashboardPage.tsx  # Founder overview — recent uploads, quick stats
│   │       ├── upload/UploadPage.tsx   # Drag-and-drop file upload → POST /upload/financials
│   │       ├── query/QueryPage.tsx     # Chat-style interface — SSE stream, 4 AgentCards
│   │       ├── simulate/SimulatePage.tsx  # Monte Carlo form + Recharts AreaChart
│   │       └── charts/ChartsPage.tsx   # Historical simulation chart browser
│   │
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── .env                            # VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_API_URL
│
├── data/synthetic/                     # Mock CSVs for local testing (no real credentials needed)
│   ├── financials.csv
│   ├── growth_metrics.csv
│   └── market_trends.csv
│
├── environment.yml                     # Conda environment (Python 3.12, pinned deps)
├── requirements.txt                    # pip deps for Docker image
├── .env.example                        # Backend env template — copy to .env and fill
├── DESIGN.md                           # Design system tokens (Claude-inspired, terracotta accent)
└── system_design.html                  # Complete interactive system design document
```

---

## Backend — Module Deep Dive

### `backend/main.py` — Application Entry Point

FastAPI application with:
- **Lifespan context manager** — starts the APScheduler news job on startup, stops it on shutdown, warms the Supabase connection pool.
- **CORS middleware** — origins loaded from `CORS_ORIGINS` env var (comma-separated list). In production: your frontend domain only. Never `*`.
- **Global exception handler** — any unhandled exception returns `{ success: false, error: { code, message } }` and never leaks stack traces or internal paths.
- **Router mounting** — auth, upload, query, simulate, charts, founders.
- **Health check** — `GET /health` returns `{ status, version, environment }`. No auth required. Used by Cloud Run liveness probe.

### `backend/config.py` — Typed Settings

Uses `pydantic-settings` with `@lru_cache`. One singleton `Settings` object loaded at startup from `.env`. All callers inject it via `Depends(get_settings)`. Properties:
- `cors_origins_list` — splits the comma-separated `CORS_ORIGINS` string into a list.
- `is_production` — `True` when `ENVIRONMENT=production`, used to disable Swagger UI in prod.

### `backend/auth/` — Authentication & Authorization

**How auth works:**
1. User calls `POST /auth/register` with email + password.
2. Backend calls Supabase Auth `sign_up` (anon key) → Supabase creates the user in `auth.users`.
3. Backend then uses the **service role key** (bypasses RLS) to insert a row into the `founders` table.
4. Returns `{ tokens: { access_token, refresh_token, expires_in }, founder: { id, email, ... } }`.

**`middleware.py` — `verify_jwt` dependency:**
- Extracts `Authorization: Bearer <token>` from every request.
- Validates the JWT signature using `SUPABASE_JWT_SECRET` (HS256).
- Fetches the founder profile from `founders` table and attaches it to the request claims.
- Any route that uses `Depends(verify_jwt)` is automatically protected.

**Endpoints:**
| Method | Path | What it does |
|--------|------|-------------|
| POST | `/auth/register` | Create Supabase user + founder profile row |
| POST | `/auth/login` | Sign in, return JWT tokens |
| POST | `/auth/refresh` | Exchange refresh token for new access token |
| POST | `/auth/logout` | Invalidate session |
| POST | `/auth/mfa/enroll` | Begin TOTP enrollment, return QR code URI |
| POST | `/auth/mfa/verify` | Verify TOTP code, upgrade session to AAL2 |
| GET | `/auth/me` | Return current founder profile |

### `backend/agents/` — 4-Agent AI Pipeline

Agents run **sequentially** — each reads the previous agent's output. The orchestrator runs them in a `ThreadPoolExecutor` (because Groq's Python client is blocking) and yields SSE events between each agent so the frontend updates in real time.

**Why sequential, not parallel?** Each agent needs the prior agent's output to reason well. MarketAgent identifies the competitive landscape; RiskAgent uses that to weight its risk factors; RevenueAgent uses both to project growth; StrategyAgent synthesises all three into a final recommendation.

| Agent | Model | Input | Output |
|-------|-------|-------|--------|
| MarketAgent | `llama-3.1-8b-instant` | question + RAG context | `market_size_assessment`, `competitor_threats`, `opportunity_areas`, `confidence` |
| RiskAgent | `llama-3.1-8b-instant` | question + RAG context + market output | `top_risks`, `risk_score`, `mitigation_strategies` |
| RevenueAgent | `llama-3.1-8b-instant` | question + RAG context + risk output | `revenue_assessment`, `growth_drivers`, `projected_mrr_range` |
| StrategyAgent | `llama-3.3-70b-versatile` | question + all 3 prior outputs | `strategy`, `immediate_actions`, `kpis_to_watch` |

All agents use `response_format={"type": "json_object"}` — Groq enforces valid JSON output. Each agent has a typed Pydantic `Output` model and a fallback response so one agent failure does not stop the pipeline.

**SSE events emitted:**
- `rag_context` — retrieved document chunks before agents start
- `agent_update` — one event per agent as it completes
- `final` — pipeline done, summary of agents ran and chunks used
- `error` — unrecoverable stream error

### `backend/rag/` — Retrieval-Augmented Generation

**Indexing flow (called after every upload):**
1. `indexer.py` — receives raw file bytes, calls `extractors.py` to get plain text, splits into overlapping 512-token chunks, embeds each chunk using `encoder.py`.
2. `encoder.py` — wraps `sentence-transformers` (`all-MiniLM-L6-v2`). Embeds each chunk into a 384-dimension float vector.
3. Chunks + embeddings stored in `document_embeddings` table (pgvector column).

**Retrieval flow (called before each query):**
1. `retriever.py` — embeds the founder's question using the same encoder.
2. Runs `SELECT ... ORDER BY embedding <=> query_vector LIMIT k` against pgvector — cosine similarity search.
3. Returns top-k `DocumentChunk` objects (text, source filename, similarity score).
4. `pipeline.py` — `RAGPipeline` class wraps indexer + retriever. `chunks_to_context()` formats chunks into a numbered list injected into agent prompts.

**Why RAG instead of just sending the whole CSV to the LLM?** Founder documents can be hundreds of pages. RAG retrieves only the most relevant 5 passages, keeping prompts short and reducing cost/latency dramatically.

### `backend/automl/monte_carlo.py` — Simulation Engine

Runs 10,000 parallel simulation paths using NumPy vectorised operations (no loop per simulation). Each path:
1. Draws a monthly growth rate from a Gaussian distribution parameterised by the chosen scenario (bear/base/bull).
2. Compounds revenue across the forecast horizon.
3. Draws a noisy burn rate (Gaussian, ±8% of base burn).
4. Tracks cumulative burn vs. available cash to compute runway.

Outputs **P10 / P50 / P90 percentiles** for revenue and runway:
- P10 = 10th percentile (bear outcome — 90% of simulations do better)
- P50 = median (most likely outcome)
- P90 = 90th percentile (bull outcome — only 10% of simulations do better)

The simulation is seeded from the founder's uploaded financial metrics (extracted from their CSV). If no upload is provided, it uses conservative defaults.

**Scenario parameters:**
| Scenario | Monthly growth μ | Std dev |
|----------|-----------------|---------|
| Bear | -1% | ±5% |
| Base | +5% | ±4% |
| Bull | +12% | ±6% |

CAC changes drag the growth mean by `cac_change × 0.3` (a 20% CAC increase reduces expected growth by 6%).

### `backend/news/` — Market News Intelligence

**`ingestion.py`** — `ingest_news_batch()`:
1. Calls NewsCatcher API for topics: "startup funding", "SaaS growth", "venture capital", "product market fit", "CAC LTV SaaS".
2. Deduplicates against URLs already in `news_articles` table.
3. For each new article, calls News-Please (`NewsPlease.from_url`) to extract full article text.
4. Persists raw article to `news_articles` table.
5. Indexes the full text into RAG with `founder_id="global"` — news is shared across all founders.
6. Logs each run to `ingestion_logs` table.

**`scheduler.py`** — APScheduler runs `ingest_news_batch` every 6 hours in a background thread. Started in the FastAPI lifespan; skipped if `NEWSCATCHER_API_KEY` is not set.

### `backend/storage/` — Data Persistence

**`supabase_client.py`** — singleton `get_supabase_client()`. Uses the **service role key** to bypass RLS for backend writes. Cached after first call.

**`gcs_client.py`** — GCP Cloud Storage client. Uploads raw files to `gs://{GCS_BUCKET_NAME}/uploads/{founder_id}/{filename}`. Returns the GCS object path for storage in the DB.

**`extractors.py`** — multi-format text extraction:
- CSV/Excel → `pandas` DataFrame → detect financial columns (revenue, burn, CAC, LTV, growth) → extract structured metrics + convert all rows to text
- PDF → `pdfminer`
- DOCX → `python-docx`
- Images (JPG/PNG) → `pytesseract` OCR
- Plain text → direct read

Financial columns detected by name matching a whitelist of known header variants (e.g. `mrr`, `monthly_recurring_revenue`, `revenue`). Extracted metrics seed the Monte Carlo simulation.

### `backend/routers/` — API Endpoints

| Router | Prefix | Endpoints |
|--------|--------|-----------|
| `upload.py` | `/upload` | `POST /upload/financials` — multipart upload, extract, index, persist |
| `query.py` | `/query` | `POST /query` — SSE stream of 4-agent pipeline |
| `simulate.py` | `/simulate` | `POST /simulate` — Monte Carlo, returns P10/P50/P90 |
| `charts.py` | `/charts` | `GET /charts` — list past simulation results |
| `founders.py` | `/founders` | `GET /founders/me`, `PATCH /founders/me` |

All routes (except `/health` and `/auth/*`) require `Depends(verify_jwt)`.

---

## Database Schema

All tables live in the `public` schema in Supabase PostgreSQL. Row Level Security (RLS) is enabled on every table. Writes from the backend use the service role key (bypasses RLS). Reads from the frontend go through the anon key + RLS policies that restrict each user to their own rows.

### `founders` (migration 001)
```sql
id           UUID  PK → auth.users(id)
email        TEXT  UNIQUE NOT NULL
full_name    TEXT
company_name TEXT
created_at   TIMESTAMPTZ
updated_at   TIMESTAMPTZ  -- auto-updated by trigger
```
RLS: `SELECT` and `UPDATE` allowed only where `auth.uid() = id`.

### `document_embeddings` (migration 002)
```sql
id           UUID  PK
founder_id   UUID  → auth.users(id)
source       TEXT  -- filename
doc_type     TEXT  -- 'financial' | 'news' | 'manual'
chunk_index  INT
text         TEXT
embedding    vector(384)   -- pgvector column
created_at   TIMESTAMPTZ
```
Indexed with `ivfflat` index on `embedding` for fast cosine search.

### `news_articles` + `ingestion_logs` (migration 003)
```sql
-- news_articles
id             UUID  PK
url            TEXT  UNIQUE  -- deduplication key
title          TEXT
author         TEXT
published_date TEXT
source         TEXT
full_text      TEXT
topics         TEXT[]
indexed        BOOLEAN  -- true after RAG indexing

-- ingestion_logs
id               UUID  PK
ingested_count   INT
skipped_count    INT
error_count      INT
duration_seconds NUMERIC
created_at       TIMESTAMPTZ
```

### `uploads` (migration 004 + 004b)
```sql
id               UUID  PK
founder_id       UUID  → auth.users(id)
filename         TEXT
file_type        TEXT
storage_path    TEXT
row_count        INT
columns          TEXT[]
is_financial     BOOLEAN
initial_metrics  JSONB  -- { revenue, burn_rate, cac, ltv, ... }
created_at       TIMESTAMPTZ
```

### `simulation_results` (migration 005)
```sql
id               UUID  PK
founder_id       UUID  → auth.users(id)
upload_id        UUID  → uploads(id)
months_ahead     INT
growth_scenario  TEXT  CHECK IN ('bear','base','bull')
forecast         JSONB  -- array of { month, p10, p50, p90 }
runway_p10       NUMERIC
runway_p50       NUMERIC
runway_p90       NUMERIC
created_at       TIMESTAMPTZ
```
Indexed on `founder_id`, `upload_id`, and `created_at DESC`.

---

## Frontend — Page by Page

### Design System (`DESIGN.md`)
Claude-inspired dark theme. Black base (`#000000`), warm terracotta accent (`#D97757`). All tokens defined as Tailwind utility classes — no arbitrary values in components.

Key patterns:
- **App card**: `rounded-2xl border border-[#1e1c1a] bg-[#0d0c0b] p-6`
- **Input**: dark bg, terracotta focus border, placeholder in `#6B6560`
- **Primary button**: solid terracotta, hover darkens to `#C9623F`
- **Animations**: Framer Motion `fadeUp` (y:24→0, opacity:0→1, 500ms) with stagger children

### `LandingPage` — `/`
Public marketing page. Glass-morphism navbar (backdrop-blur, 80% black bg). Hero section with animated headline. Feature grid explaining the 4-agent pipeline, RAG, Monte Carlo. CTAs to register and login.

### `LoginPage` + `RegisterPage` — `/auth/*`
Form components that call `POST /auth/login` and `POST /auth/register`. On success, store the JWT access token in `localStorage`, update Supabase session, and redirect to `/dashboard`.

### `ProtectedRoute`
Checks `supabase.auth.getSession()`. If no session: redirect to `/auth/login`. Wraps all app routes in `App.tsx`.

### `Layout`
Persistent sidebar with navigation links: Dashboard, Upload, Ask AI, Simulate, Charts. Sidebar active state uses terracotta highlight. `<Outlet />` renders the active page to the right.

### `DashboardPage` — `/dashboard`
Shows the founder's profile (company name, email), count of uploads, and links to the main actions.

### `UploadPage` — `/upload`
Drag-and-drop zone (or click to browse). Accepts CSV, Excel, PDF, DOCX, images, TXT. Calls `POST /upload/financials` as `multipart/form-data`. Shows upload result: filename, type, row count, detected columns, whether financial columns were found (direct simulation seed vs. AI-extracted).

### `QueryPage` — `/query`
- Select an uploaded document from a dropdown (or leave blank for a general question).
- Type a question. Press Enter to submit (Shift+Enter for newline).
- Calls `streamQuery()` from `api/client.ts` which opens a `fetch` SSE stream to `POST /query`.
- Each `agent_update` event appends an `AgentCard` to the message list with the agent name color-coded and the summary field displayed.
- Streaming spinner shown while pipeline runs. "Analysis complete" shown on `final` event.

### `SimulatePage` — `/simulate`
- Form with: document selector, months slider (1–24), bear/base/bull selector, CAC % slider, burn % slider.
- Calls `POST /simulate` and receives `{ forecast, runway_p10, runway_p50, runway_p90, simulation_runs }`.
- Renders three runway stat cards (P10/P50/P90) and a Recharts `AreaChart` with three area series (P10, P50, P90) using gradient fills matching the design system colors.
- Custom tooltip shows formatted dollar amounts for each percentile.

### `ChartsPage` — `/charts`
Fetches historical simulation results from `GET /charts` and renders past simulations for comparison.

---

## API Reference

### Response Envelope
```json
// Success
{ "success": true, "data": { ... } }

// Error
{ "success": false, "error": { "code": "ERR_001", "message": "Human-readable message" } }
```

### Key Endpoints

```
GET  /health                        Liveness check — no auth
POST /auth/register                 { email, password, full_name?, company_name? }
POST /auth/login                    { email, password }
POST /auth/refresh                  { refresh_token }
POST /auth/logout                   { refresh_token }
POST /auth/mfa/enroll               Bearer token required — returns TOTP URI
POST /auth/mfa/verify               { factor_id, challenge_id, code }
GET  /auth/me                       Bearer token required — returns founder profile

POST /upload/financials             multipart/form-data, file field
POST /query                         { question, upload_id? } → SSE stream
POST /simulate                      { upload_id, months_ahead, growth_scenario, cac_change_pct, burn_change_pct }
GET  /charts                        Bearer token — returns past simulation list
GET  /founders/me                   Bearer token — founder profile
PATCH /founders/me                  { full_name?, company_name? }
```

---

## Environment Variables

### Backend (`.env`)
| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_KEY` | Yes | Anon/public key (used for auth sign-up/in) |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Service role key (backend DB writes, bypasses RLS) |
| `SUPABASE_JWT_SECRET` | Yes | Signs JWT tokens — from Supabase → Settings → API → JWT Settings |
| `GROQ_API_KEY` | Yes | Groq API key — powers all 4 agents |
| `GCS_BUCKET_NAME` | Prod | GCP bucket for raw file storage |
| `GCP_PROJECT_ID` | Prod | GCP project |
| `NEWSCATCHER_API_KEY` | Optional | News ingestion — scheduler disabled if missing |
| `ENVIRONMENT` | Yes | `development` \| `production` |
| `CORS_ORIGINS` | Yes | Comma-separated allowed origins, e.g. `http://localhost:5173` |
| `LOG_LEVEL` | No | `INFO` (default) |
| `PORT` | No | `8000` (default) |

### Frontend (`frontend/.env`)
| Variable | Description |
|----------|-------------|
| `VITE_SUPABASE_URL` | Same as backend `SUPABASE_URL` |
| `VITE_SUPABASE_ANON_KEY` | Same as backend `SUPABASE_KEY` (the anon key — safe for browser) |
| `VITE_API_URL` | Backend URL — `http://localhost:8000` for local dev |

---

## Local Development — Full Setup

### Prerequisites
- Miniconda or Anaconda (Python 3.12)
- Node.js 20+
- A Supabase project (free tier at supabase.com)
- A Groq API key (free tier at console.groq.com/keys)

### 1. Backend setup

```bash
# Clone repo and create conda env
conda env create -f environment.yml
conda activate foundr-ai

# Copy and fill env vars
cp .env.example .env
# Edit .env with your Supabase and Groq credentials

# Run DB migrations (Supabase Dashboard → SQL Editor, run each file in order)
# 001 → 002 → 003 → 004 → 004b → 005

# Start backend
uvicorn backend.main:app --reload --port 8000
```

Verify: open `http://localhost:8000/health` → should return `{"status":"ok"}`
API docs: `http://localhost:8000/docs`

### 2. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Verify: open `http://localhost:5173`

### 3. Run tests

```bash
# From project root, conda env active
pytest backend/tests/ -v --cov=backend --cov-report=term-missing
```

---

## Security Model

- **JWT verification** on every protected route via `verify_jwt` FastAPI dependency.
- **RLS** on every Supabase table — database-level row isolation per user.
- **Service role key** only used server-side, never exposed to frontend.
- **Anon key** in frontend — safe because RLS prevents cross-user data access.
- **Parameterised queries only** — Supabase Python client uses prepared statements internally.
- **No secrets in logs** — pino/structlog redacts `password`, `token`, `apiKey`, `privateKey`.
- **Input validation** — all request bodies are Pydantic models with strict types and field validators.
- **CORS** — restrictive origin list from env, never `*` in production.
- **File type validation** — accepted extensions whitelist at upload; content is not trusted blindly.

---

## Layer Build Status

| Layer | Description | Status |
|-------|-------------|--------|
| 0 | Environment setup (Conda, deps, structure) | ✅ Complete |
| 1 | System design document | ✅ Complete |
| 2 | Authentication & security (Supabase JWT, MFA, middleware) | ✅ Complete |
| 3 | Backend API (FastAPI, routers, config, CORS, health) | ✅ Complete |
| 4 | Agent orchestration (4-agent pipeline, SSE, Groq) | ✅ Complete |
| 5 | RAG pipeline (pgvector, embeddings, retriever) | ✅ Complete |
| 6 | News ingestion (NewsCatcher, News-Please, scheduler) | ✅ Complete |
| 7 | AutoML & simulation (Monte Carlo, P10/P50/P90) | ✅ Complete |
| 8 | Data & storage (Supabase client, GCS, extractors) | ✅ Complete |
| 9 | Frontend (React, Vite, all pages, design system) | ✅ Complete |
| 10 | Deployment & CI/CD (Docker, Cloud Run, Firebase) | Planned |

---

## License

MIT License.
