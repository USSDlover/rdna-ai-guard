# ⚙️ RDNA AI GUARD // BACKEND_CORE

This is the asynchronous Python gateway for RDNA AI Guard. It handles low-level ingestion hooks, deterministic FinSec triage mocking, and pushes high-fidelity telemetry packets directly to the Angular engine over low-latency Server-Sent Events (SSE).

---

## 🚀 LOCAL EXECUTION PROTOCOL

### 1. Environment Synthesis
Navigate to the backend node and set up a clean virtual environment space:
```bash
cd backend
python -m venv venv

# Activate Environment
source venv/bin/activate  # macOS/Linux
.\venv\Scripts\activate   # Windows

```

### 2. Dependencies Ingestion

Compile all core networking and AI abstraction requirements:

```bash
pip install --upgrade pip
pip install -r requirements.txt

```

### 3. Ignition Order

Fire up the local developmental ASGI runtime environment:

```bash
uvicorn app.main:app --reload --port 8000

```

* 📡 **Live Swagger Docs Gateway:** `http://localhost:8000/docs`
* 🧪 **Streaming Verification Node:** `curl http://localhost:8000/api/v1/telemetry/stream`

---

## 🔬 ARCHITECTURAL MAP

* `app/main.py`: Gateway router initializing global CORS allowances for port `4200`.
* `app/core/config.py`: Configuration layer mapping local Ollama endpoints and parameters.
* `app/models/schemas.py`: Pydantic definitions enforcing runtime payload integrity.
* `app/network/router.py`: Dual-purpose telemetry multiplexer:
* `POST /triage`: Low-latency mock calculation simulating local Gemma 4 schemas.
* `GET /stream`: Async infinite event-stream injector yielding high-risk spikes on a 3:1 pattern.
