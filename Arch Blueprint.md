# Local Prompt Strategy (Zero-Token Triage)

We use Gemma 4 to ingest raw telementry chunk and output a clean, minified JSON object containing a `risk_score` and a `route`.

Ollama `Modelfile` to lock down this behavior:

```Dockerfile
# Modelfile for RDNA AI Guard Router
FROM gemma4:12b

# Enforce crisp, deterministic JSON routing outputs
SYSTEM """
You are the core routing gate for RDNA AI Guard. Analyze the incoming telemetry packet.
Determine if there are indicators of network exploits (credential stuffing, API scrapers) or financial fraud (rapid transaction loops, cross-border mules).
Output strictly valid JSON with no conversational text.

Schema:
{
  "risk_score": <int 0-100>,
  "escalate": <bool>,
  "primary_vector": "NONE" | "CYBER" | "FRAUD" | "BOTH"
}

If risk_score > 60, set escalate to true. Otherwise, false.
"""

PARAMETER temperature 0.0
PARAMETER top_p 0.1
```

# FastAPI Routing Controller (app/network/router.py)

Here is how our backend handover the packet from Scapy to Ollama

```python
import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any
import json

router = APIRouter(prefix="/v1/telemetry", tags=["Routing"])

OLLAMA_URL = "http://localhost:11434/api/chat"

class TelemetryPayload(BaseModel):
    source_ip: str
    request_path: str
    payload_size: int
    transaction_amount: float
    account_token: str
    velocity_count_1m: int

def trigger_cloud_agents(payload: Dict[str, Any], vector: str):
    """
    Background Task: Escalates high-risk payloads to Fireworks Cloud API (LangGraph loop)
    """
    print(f"⚠️ Escalating to Cloud Agent Mesh for deep reasoning. Focus: {vector}")
    # Integration with LangGraph/CrewAI goes here...

@router.post("/triage")
async def triage_incoming_logs(data: TelemetryPayload, background_tasks: BackgroundTasks):
    # Package telemetry payload for Gemma 4
    prompt_content = f"Analyze log: {data.model_dump_json()}"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(OLLAMA_URL, json={
                "model": "gemma4:12b",
                "messages": [{"role": "user", "content": prompt_content}],
                "stream": False,
                "format": "json" # Enforces JSON schema on Gemma 4
            })
            
            result_json = response.json()
            routing_decision = json.loads(result_json["message"]["content"])
            
            # Actionable Conditional Routing Hook
            if routing_decision.get("escalate"):
                background_tasks.add_task(
                    trigger_cloud_agents, 
                    data.model_dump(), 
                    routing_decision.get("primary_vector")
                )
                return {
                    "status": "ESCALATED",
                    "triage": routing_decision,
                    "tokens_spent": 0 # Local execution metric
                }
                
            return {
                "status": "PASSED",
                "triage": routing_decision,
                "tokens_spent": 0
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ollama routing fault: {str(e)}")
```

# Monorepo Architecture

```plaintext
rdna-ai-guard/
├── .github/                  # CI/CD workflows (if needed)
├── backend/                  # FastAPI + Scapy network engine
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # Angular 19+ Dashboard 
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml        # Orchestrates FE, BE, DB, and Ollama network
├── Modelfile                 # Custom Gemma 4 structured configuration
└── README.md                 # Your main pitch, docs, and setup instructions
```

## Orchestration Blueprint

`docker-compose.yml`

```yaml
version: '3.8'

services:
  # 1. Database Layer
  postgres:
    image: postgres:16-alpine
    container_name: rdna-db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: guard_password
      POSTGRES_DB: rdna_guard
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - rdna-network

  # 2. Local AI Inference Layer (Ollama + Gemma 4)
  ollama:
    image: ollama/ollama:latest
    container_name: rdna-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    # Note: If running on native Linux with AMD GPUs, pass the ROCm/amdgpu drivers here
    networks:
      - rdna-network

  # 3. Python Backend Layer
  backend:
    build: ./backend
    container_name: rdna-backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:guard_password@postgres:5432/rdna_guard
      - OLLAMA_HOST=http://ollama:11434
      - FIREWORKS_API_KEY=${FIREWORKS_API_KEY}
    depends_on:
      - postgres
      - ollama
    networks:
      - rdna-network

  # 4. Angular Frontend Layer
  frontend:
    build: ./frontend
    container_name: rdna-frontend
    ports:
      - "4200:4200"
    depends_on:
      - backend
    networks:
      - rdna-network

volumes:
  pgdata:
  ollama_data:

networks:
  rdna-network:
    driver: bridge
```