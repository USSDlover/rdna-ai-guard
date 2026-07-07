# RDNA AI Guard

[![AMD Hackathon Track](https://img.shields.io/badge/AMD_ACT_II-Unicorn_Track-FE5F55?style=flat-square&logo=amd&logoColor=white)](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii/rdna-rebels)
[![Stack](https://img.shields.io/badge/Stack-FastAPI_%2B_Angular-2D3142?style=flat-square)](https://github.com)

Unified FinSec telemetry platform for the AMD Developer Hackathon. The backend ingests and triages security events over FastAPI; the Angular control grid consumes a live Server-Sent Events (SSE) stream for real-time threat visualization.

---

## Repository Layout

```text
RDNA Guard/
├── backend/                  # FastAPI async API (Python 3.12)
│   ├── app/
│   │   ├── core/             # Settings and configuration
│   │   ├── models/           # Pydantic schemas
│   │   └── network/          # Telemetry triage + SSE routes
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                 # Angular control station
│   ├── src/app/
│   │   ├── core/             # SSE telemetry stream service
│   │   └── features/         # Dashboard shell + cyber grid
│   ├── nginx.conf
│   └── Dockerfile
└── docker-compose.yml        # Multi-container orchestration
```

---

## Prerequisites

| Tool | Version | Used For |
|------|---------|----------|
| Docker | 24+ | Unified Compose stack |
| Docker Compose | v2+ | Multi-service orchestration |
| Python | 3.12+ | Native backend development |
| Node.js | 20+ | Native frontend development |
| npm | 10+ | Frontend package management |

Optional (for future AI routing integration):

- **Ollama** running locally on `http://localhost:11434`

---

## The Unified Vector (Docker Compose)

Run both the backend and frontend together with a single command from the repository root.

### 1. Start the stack

```bash
docker compose up --build
```

To run detached:

```bash
docker compose up --build -d
```

### 2. Access the services

| Service | URL | Description |
|---------|-----|-------------|
| Frontend (Control Grid) | http://localhost:4200 | Angular dashboard served by Nginx |
| Backend (API Gateway) | http://localhost:8000 | FastAPI root |
| API Documentation | http://localhost:8000/docs | Interactive Swagger UI |
| Health Check | http://localhost:8000/health | Service status probe |
| SSE Telemetry Stream | http://localhost:8000/api/v1/telemetry/stream | Live event stream |

### 3. Stop the stack

```bash
docker compose down
```

### Compose topology

- **backend** — built from `./backend`, exposed on `8000:8000`
- **frontend** — built from `./frontend`, exposed on `4200:80` (container Nginx listens on port 80)
- Both services share the `rdna-network` bridge network
- `frontend` declares `depends_on: backend` so the API container starts first

### Environment overrides (Compose)

The backend container receives these environment variables:

```env
OLLAMA_HOST=http://host.docker.internal:11434
GEMMA_MODEL=gemma4:12b
```

`host.docker.internal` allows the containerized backend to reach Ollama running on the host machine. Ensure Ollama is started locally if you plan to integrate live model routing.

---

## The Isolated Vectors (Independent Local Execution)

Use these paths when you need to debug one layer without rebuilding containers.

### Backend only (native Python)

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Start the ASGI server with hot reload
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify the backend:

```bash
curl http://localhost:8000/health
curl -N http://localhost:8000/api/v1/telemetry/stream
```

API docs: http://localhost:8000/docs

Optional `.env` in `backend/` (loaded automatically by the app):

```env
PROJECT_NAME=RDNA AI Guard
API_V1_STR=/api/v1
OLLAMA_HOST=http://localhost:11434
GEMMA_MODEL=gemma4:12b
```

---

### Frontend only (native Angular)

The frontend expects the backend SSE endpoint at `http://127.0.0.1:8000`. Start the backend first (see above) or run only the mock UI shell without live data.

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm start
```

The dev server runs at http://localhost:4200 with live reload.

Build a production bundle locally:

```bash
npm run build
```

Output directory: `frontend/dist/frontend/browser`

---

## Port Reference

| Port | Service | Context |
|------|---------|---------|
| `4200` | Frontend | `ng serve` (dev) or Docker Compose (`4200:80`) |
| `8000` | Backend | `uvicorn` (dev) or Docker Compose (`8000:8000`) |
| `11434` | Ollama | Host-only AI routing endpoint (optional) |

---

## API Endpoints (Backend)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health probe |
| `POST` | `/api/v1/telemetry/triage` | Deterministic risk triage (Ollama-style response) |
| `GET` | `/api/v1/telemetry/stream` | Infinite SSE telemetry stream |

CORS is configured for `http://localhost:4200` so the Angular app can consume the API from both native dev and Docker-mapped ports.

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

Stop the conflicting process or change the host port mapping in `docker-compose.yml`.

**Frontend shows no telemetry rows**

Confirm the backend is running and reachable at http://127.0.0.1:8000/health before opening the Cyber Grid dashboard.

**Docker build fails on frontend**

Ensure `package-lock.json` is present in `frontend/`. The Dockerfile uses `npm ci` for reproducible installs.

**Angular routes return 404 in Docker**

The Nginx config in `frontend/nginx.conf` uses `try_files` fallback to `index.html` for client-side routing.

---

## Team

Built by **RDNA Rebels** for the **AMD Developer Hackathon ACT II**.

- Project workspace: [LabLab.ai // RDNA Rebels](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii/rdna-rebels)
