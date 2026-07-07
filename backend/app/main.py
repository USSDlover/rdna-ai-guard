from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.network import router as network_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Tactical FinSec Telemetry Routing Engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(network_router.router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, object]:
    return {
        "status": "ONLINE",
        "project": settings.PROJECT_NAME,
        "systems": {
            "ingestion_gate": "READY",
            "ollama_bridge": "ACTIVE",
        },
    }
