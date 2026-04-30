# FoundrAI

**Autonomous AI Advisory Platform for Startup Founders**

FoundrAI helps startup founders make data-driven decisions by combining
multi-agent AI orchestration, retrieval-augmented generation (RAG),
AutoML-powered revenue forecasting, Monte Carlo scenario simulation, and
real-time market news intelligence — all delivered through a modern React
frontend and a FastAPI backend deployed on GCP.

---

## What It Does

A founder uploads their financial CSVs (revenue, burn rate, CAC, LTV,
growth metrics) and asks natural-language questions:

- *"What is my runway if CAC increases by 20% next quarter?"*
- *"Which market segment should I double down on?"*
- *"What are the biggest risks to my current growth model?"*

FoundrAI responds with a structured multi-agent analysis, RAG-grounded
citations from the founder's own data and live news, revenue forecasts
with P10/P50/P90 confidence bands, and interactive BI dashboards.

---

## Tech Stack (Summary)

| Layer | Tech |
|-------|------|
| Backend API | FastAPI + Uvicorn (Python 3.12) |
| AI Agents | AutoGen + Groq (Llama 3.3-70b, Llama 3.1-8b, DeepSeek-R1) |
| RAG | Haystack + ColBERT (RAGatouille) + pgvector |
| News | NewsCatcher OSS + News-Please + APScheduler |
| AutoML | FLAML + NumPy/SciPy Monte Carlo |
| Database | Supabase (PostgreSQL 15 + pgvector) |
| Storage | GCP Cloud Storage |
| Frontend | React 18 + Vite + ShadCN UI + TailwindCSS |
| Dashboards | Apache Superset + Recharts |
| Deployment | Docker → GCP Cloud Run + Firebase Hosting |
| CI/CD | GitHub Actions |

---

## Prerequisites

- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or Anaconda 24.x
- Python 3.12 (managed by Conda — do not use system Python)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for local Supabase + Superset)
- A Supabase project ([free tier](https://supabase.com))
- A Groq API key ([free tier](https://console.groq.com/keys), ~10K tok/min)
- A GCP project with Cloud Storage enabled (for production; optional for local dev)

---

## Local Development Setup

### 1. Clone and enter the repository

```bash
git clone https://github.com/your-org/foundr-ai.git
cd foundr-ai
```

### 2. Create and activate the Conda environment

```bash
conda env create -f environment.yml
conda activate foundr-ai
```

This installs all Python dependencies pinned at exact versions. The
environment name is `foundr-ai`.

### 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in the required values:

| Variable | Where to get it |
|----------|----------------|
| `SUPABASE_URL` | Supabase Dashboard → Settings → API |
| `SUPABASE_KEY` | Supabase Dashboard → Settings → API (anon key) |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Dashboard → Settings → API (service role) |
| `SUPABASE_JWT_SECRET` | Supabase Dashboard → Settings → API → JWT Settings |
| `GROQ_API_KEY` | [console.groq.com/keys](https://console.groq.com/keys) |
| `NEWSCATCHER_API_KEY` | [newscatcherapi.com](https://www.newscatcherapi.com) |

### 4. Run Supabase migrations

Apply the SQL migration files in order against your Supabase project:

```bash
# Using Supabase CLI (recommended)
supabase db push

# Or manually via Supabase Dashboard → SQL Editor, run each file in order:
# backend/storage/migrations/001_create_founders.sql
# backend/storage/migrations/002_create_document_embeddings.sql
# backend/storage/migrations/003_create_news_tables.sql
# backend/storage/migrations/004_create_uploads.sql
# backend/storage/migrations/005_create_queries.sql
# backend/storage/migrations/006_create_simulations.sql
```

### 5. Start local services (Docker)

```bash
docker compose -f docker/docker-compose.yml up -d
```

This starts Apache Superset on port 8088. Local PostgreSQL is optional if
you are using the hosted Supabase project.

### 6. Start the FastAPI backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive API docs: `http://localhost:8000/docs`

### 7. Start the frontend (when Layer 9 is built)

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## Running Tests

```bash
# From project root with conda env active
pytest backend/tests/ -v --cov=backend --cov-report=term-missing
```

Target coverage: ≥ 80% across all backend modules.

---

## Project Structure

```
foundr-ai/
├── system_design.html          # Complete system design document (Layer 1)
├── environment.yml             # Conda environment definition
├── requirements.txt            # pip-only deps for Cloud Run Docker image
├── .env.example                # Environment variable template
│
├── backend/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Typed settings (pydantic-settings)
│   ├── auth/                   # JWT middleware + auth endpoints
│   ├── agents/                 # AutoGen multi-agent orchestration
│   ├── rag/                    # Haystack + ColBERT RAG pipeline
│   ├── news/                   # NewsCatcher ingestion + APScheduler
│   ├── automl/                 # FLAML training + Monte Carlo simulation
│   ├── storage/                # Supabase + GCS client wrappers
│   ├── routers/                # FastAPI route handlers
│   └── tests/                  # Pytest test suite
│
├── frontend/                   # React 18 + Vite + ShadCN UI (Layer 9)
├── docker/                     # Dockerfile + docker-compose.yml
├── .github/workflows/          # GitHub Actions CI/CD pipeline
└── data/synthetic/             # Mock CSVs for local testing
```

---

## Layer Build Status

| Layer | Description | Status |
|-------|-------------|--------|
| 0 | Environment Setup | ✅ Complete |
| 1 | System Design Document | Planned |
| 2 | Authentication & Security | Planned |
| 3 | Backend API Layer | Planned |
| 4 | Agent Orchestration | Planned |
| 5 | RAG Pipeline | Planned |
| 6 | News Ingestion Pipeline | Planned |
| 7 | AutoML & Simulation Engine | Planned |
| 8 | Data & Storage Layer | Planned |
| 9 | Visualization Layer | Planned |
| 10 | Deployment & CI/CD | Planned |

---

## Contributing

This is a prototype-to-production build. Follow the layer build order.
Never skip layers — each layer's tests must pass before the next begins.

---

## License

MIT License. See LICENSE file.
