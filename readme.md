# RDNA AI Guard

[![AMD Hackathon Track](https://img.shields.io/badge/AMD_ACT_II-Unicorn_Track-FE5F55?style=flat-square&logo=amd&logoColor=white)](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii/rdna-rebels)
[![Stack](https://img.shields.io/badge/Stack-FastAPI_%2B_Angular-2D3142?style=flat-square)](https://github.com)

Unified FinSec telemetry platform for the AMD Developer Hackathon. The backend ingests and triages security events over FastAPI with local Ollama (Gemma) and cloud LangGraph escalation (Fireworks AI); the Angular control grid consumes a live Server-Sent Events (SSE) stream for real-time threat visualization.

---

## Repository Layout

```text
RDNA Guard/
├── backend/                      # FastAPI async API (Python 3.12)
│   ├── app/
│   │   ├── ai/                   # Ollama Gemma triage client + response models
│   │   ├── agents/                 # LangGraph multi-agent cloud escalation
│   │   ├── core/                   # Settings, DB, SSE broadcast manager
│   │   ├── models/                 # SQLModel + Pydantic schemas
│   │   ├── network/                # Telemetry triage + SSE routes
│   │   ├── services/               # PostgreSQL telemetry persistence
│   │   └── scripts/                # CLI utilities for testing & demo data
│   ├── test_ai_301_integration.py
│   ├── test_ai_302_integration.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                     # Angular control station
│   ├── src/app/
│   │   ├── core/                 # SSE stream + shared telemetry state
│   │   └── features/             # Cyber grid, ledger audit, dashboard shell
│   ├── nginx.conf
│   └── Dockerfile
└── docker-compose.yml            # Postgres, Ollama, backend, frontend
```

---

## Prerequisites

| Tool | Version | Used For |
|------|---------|----------|
| Docker | 24+ | Unified Compose stack |
| Docker Compose | v2+ | Multi-service orchestration |
| Python | 3.12+ | Native backend development & scripts |
| Node.js | 20+ | Native frontend development |
| npm | 10+ | Frontend package management |

Optional for cloud escalation:

- **Fireworks AI API key** — set `FIREWORKS_API_KEY` in `backend/.env` for live LangGraph agents

---

## The Unified Vector (Docker Compose)

Run the full stack from the repository root.

### 1. Start the stack

```bash
docker compose up --build
```

Detached mode:

```bash
docker compose up --build -d
```

### 2. Access the services

| Service | URL | Description |
|---------|-----|-------------|
| Frontend (Control Grid) | http://localhost:4200 | Angular dashboard (Nginx) |
| Backend (API Gateway) | http://localhost:8000 | FastAPI root |
| API Documentation | http://localhost:8000/docs | Interactive Swagger UI |
| Health Check | http://localhost:8000/health | Service status probe |
| SSE Telemetry Stream | http://localhost:8000/api/v1/telemetry/stream | Live event stream |
| PostgreSQL | localhost:5432 | `rdna_guard` database |
| Ollama | http://localhost:11434 | Local Gemma inference |

### 3. Stop the stack

```bash
docker compose down
```

### Compose topology

| Service | Role |
|---------|------|
| `postgres` | PostgreSQL 16 — telemetry persistence |
| `ollama` | Local LLM runtime (Gemma model pull on startup) |
| `backend` | FastAPI — triage, SSE, LangGraph escalation |
| `frontend` | Angular app served by Nginx (`4200:80`) |

All services share the `rdna-network` bridge. The backend waits for Postgres and Ollama health checks before starting.

### Environment variables (`backend/.env`)

Copy `backend/.env.example` to `backend/.env` and adjust as needed:

```env
PROJECT_NAME=RDNA_AI_Guard
API_V1_STR=/api/v1
OLLAMA_HOST=http://localhost:11434
GEMMA_MODEL=gemma4:12b
FIREWORKS_API_KEY=your_fireworks_api_key_here
FIREWORKS_MODEL=accounts/fireworks/models/llama-v3p1-70b-instruct
DATABASE_URL=postgresql+asyncpg://postgres:guard_password@localhost:5432/rdna_guard
```

In Docker Compose, `DATABASE_URL` and `OLLAMA_HOST` are overridden to point at container service names.

---

## The Isolated Vectors (Independent Local Execution)

### Backend only (native Python)

```bash
cd backend

python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify:

```bash
curl http://localhost:8000/health
curl -N http://localhost:8000/api/v1/telemetry/stream
```

---

### Frontend only (native Angular)

The frontend expects the backend at `http://127.0.0.1:8000`. Start the backend first.

```bash
cd frontend
npm install
npm start
```

Dev server: http://localhost:4200

Production build:

```bash
npm run build
```

---

## API Endpoints (Backend)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health probe |
| `POST` | `/api/v1/telemetry/triage` | Local Gemma triage → PostgreSQL → SSE → optional cloud escalation |
| `POST` | `/api/v1/telemetry/seed` | Fast mock event injection (`?count=1`–`20`) for dev/testing |
| `GET` | `/api/v1/telemetry/stream` | SSE stream (replays last 50 DB events, then live broadcast) |

**Triage pipeline:** Incoming packet → Ollama (Gemma) → persisted to PostgreSQL → broadcast via SSE. If status is `ESCALATED`, LangGraph runs asynchronously (CyberSec + Anti-Fraud → Synthesizer) via Fireworks AI, then re-broadcasts the enriched event.

---

## Scripts & Testing Utilities

All commands below are run from the `backend/` directory with your virtual environment activated.

### Operational scripts (`backend/app/scripts/`)

These are CLI tools for generating demo traffic and validating integrations during development.

| Script | Purpose | When to use |
|--------|---------|-------------|
| `generate_e2e_data.py` | Full end-to-end demo data generator | Populate the Angular dashboards with realistic traffic |
| `test_cloud_escalation.py` | LangGraph + Fireworks escalation verifier | Confirm cloud multi-agent loop for CYBER and FRAUD |
| `simulate_traffic.py` | Continuous triage traffic loop | Soak-test SSE + DB under steady packet load |
| `test_triage_api.py` | Simple HTTP triage smoke test | Quick check that `/telemetry/triage` + Ollama respond |
| `test_ollama_direct.py` | Direct Ollama `/api/chat` diagnostic | Isolate Ollama connectivity from FastAPI |

#### `generate_e2e_data.py` — End-to-end demo data

Exercises: health check → fast seed → full Ollama triage → SSE → LangGraph escalation.

Populates all frontend surfaces: Cyber Grid, Ledger Audit, and global threat toasts (`risk_score > 85`).

```bash
# Recommended first run (seed + triage scenarios + SSE watch)
python -m app.scripts.generate_e2e_data

# Fast baseline only (no Ollama wait)
python -m app.scripts.generate_e2e_data --skip-triage --seed 20

# Continuous live traffic
python -m app.scripts.generate_e2e_data --continuous --interval 4

# Longer SSE observation window
python -m app.scripts.generate_e2e_data --watch-sse 90 --escalation-wait 25
```

| Flag | Default | Description |
|------|---------|-------------|
| `--seed` | `12` | Mock events via `POST /telemetry/seed` |
| `--skip-seed` | off | Skip fast seed phase |
| `--skip-triage` | off | Skip Ollama triage scenarios |
| `--continuous` | off | Loop triage until Ctrl+C |
| `--watch-sse` | `45` | Seconds to listen on SSE in parallel (`0` = off) |
| `--escalation-wait` | `15` | Wait after triage for cloud enrichment rebroadcast |

---

#### `test_cloud_escalation.py` — Multi-agent cloud escalation (AI-302)

Validates the LangGraph workflow: **CyberSec Specialist** ∥ **Anti-Fraud Specialist** → **Synthesizer**.

Tests both **CYBER** and **FRAUD** escalation paths and checks `payload_metadata.cloud_escalation` enrichment via SSE.

```bash
# Direct LangGraph test (fast, no HTTP/Ollama)
python -m app.scripts.test_cloud_escalation --mode graph

# Full API + SSE end-to-end (requires running backend + Ollama + Postgres)
python -m app.scripts.test_cloud_escalation --mode api

# Both phases
python -m app.scripts.test_cloud_escalation

# Fail if Fireworks key is missing (reject mock client)
python -m app.scripts.test_cloud_escalation --require-fireworks
```

| Flag | Default | Description |
|------|---------|-------------|
| `--mode` | `all` | `graph`, `api`, or `all` |
| `--require-fireworks` | off | Fail when `FIREWORKS_API_KEY` is unset |
| `--enrichment-timeout` | `90` | Seconds to wait per scenario for cloud SSE update |
| `--base-url` | `http://127.0.0.1:8000` | FastAPI base URL for API mode |

**Success criteria per scenario:**
- `cyber_analysis` + `cyber_score` from Node A
- `fraud_analysis` + `fraud_score` from Node B
- `synthesized_narrative` from Synthesizer
- `provider: "fireworks"` in enriched event metadata (when API key is set)

---

#### `simulate_traffic.py` — Continuous traffic generator

Posts triage payloads in an infinite loop with random delays (0.5–2.5s). Useful for watching the live dashboard update under load.

```bash
python -m app.scripts.simulate_traffic
```

Requires backend running on `http://127.0.0.1:8000`. Press Ctrl+C to stop.

---

#### `test_triage_api.py` — Triage endpoint smoke test

Sends one normal and one high-risk payload to `POST /api/v1/telemetry/triage` and prints the Gemma triage response.

```bash
python -m app.scripts.test_triage_api
```

---

#### `test_ollama_direct.py` — Raw Ollama diagnostic

Bypasses FastAPI and calls Ollama `/api/chat` directly with `format: "json"`. Use when triage fails to isolate whether the issue is Ollama or the backend wrapper.

```bash
python -m app.scripts.test_ollama_direct
```

---

### Integration test suites (`backend/`)

Automated unittest suites with mocked HTTP/Ollama/Fireworks for CI and regression checks. No running services required for most tests.

| File | Task | What it verifies |
|------|------|------------------|
| `test_ai_301_integration.py` | AI-301 | Ollama client parsing, lifespan preload/unload, triage → DB → SSE wiring |
| `test_ai_302_integration.py` | AI-302 | LangGraph nodes, graph compile, cloud escalation persistence + rebroadcast |

```bash
cd backend

# AI-301: Ollama integration + triage pipeline
python test_ai_301_integration.py

# AI-302: LangGraph multi-agent escalation
python test_ai_302_integration.py
```

Both exit with code `0` on success, `1` on failure.

---

## Recommended verification workflow

Run these in order after starting the stack:

```bash
# 1. Start services
docker compose up --build -d

# 2. Run integration tests (from backend/, venv active)
python test_ai_301_integration.py
python test_ai_302_integration.py

# 3. Populate dashboards
python -m app.scripts.generate_e2e_data

# 4. Verify cloud escalation (with FIREWORKS_API_KEY set)
python -m app.scripts.test_cloud_escalation --require-fireworks

# 5. Open frontend
#    Cyber Grid:    http://localhost:4200/dashboard/cyber-grid
#    Ledger Audit:  http://localhost:4200/dashboard/ledger-audit
```

Click any row in either dashboard to open the detail modal — escalated events show local Gemma triage plus cloud CyberSec / Anti-Fraud analysis when enrichment has completed.

---

## Port Reference

| Port | Service | Context |
|------|---------|---------|
| `4200` | Frontend | `ng serve` (dev) or Docker Compose (`4200:80`) |
| `8000` | Backend | `uvicorn` (dev) or Docker Compose (`8000:8000`) |
| `5432` | PostgreSQL | Telemetry persistence |
| `11434` | Ollama | Local Gemma inference |

---

## Troubleshooting

**Port already in use**

```bash
# Windows
netstat -ano | findstr :8000
netstat -ano | findstr :4200

# macOS / Linux
lsof -i :8000
lsof -i :4200
```

**Frontend shows no telemetry rows**

1. Confirm backend health: `curl http://127.0.0.1:8000/health`
2. Seed or generate data: `python -m app.scripts.generate_e2e_data --skip-triage --seed 10`
3. Check SSE: `curl -N http://127.0.0.1:8000/api/v1/telemetry/stream`

**Data disappears when switching dashboards**

Telemetry state is shared at the root level (`TelemetryStateService`). If you see empty tables after navigation, hard-refresh the browser after pulling the latest frontend build.

**Triage times out**

First Ollama inference after cold start can take 1–3 minutes. Ensure `gemma4:12b` is pulled: `ollama list`. Use `test_ollama_direct.py` to isolate.

**Cloud escalation shows "pending" in detail modal**

LangGraph runs asynchronously after local triage. Wait ~15–90s or run `test_cloud_escalation.py --mode api` to verify enrichment. Set `FIREWORKS_API_KEY` for live Fireworks agents (otherwise mock client is used).

**Docker build fails on frontend**

Ensure `package-lock.json` is present in `frontend/`. The Dockerfile uses `npm ci`.

**Angular routes return 404 in Docker**

The Nginx config in `frontend/nginx.conf` uses `try_files` fallback to `index.html` for client-side routing.

---

## Team

Built by **RDNA Rebels** for the **AMD Developer Hackathon ACT II**.

- Project workspace: [LabLab.ai // RDNA Rebels](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii/rdna-rebels)
