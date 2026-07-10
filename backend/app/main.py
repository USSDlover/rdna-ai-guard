from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.ai.ollama_client import preload_gemma_model, unload_gemma_model
from app.core.config import settings
from app.core.db import init_db
from app.network import router as network_router

# Resolved relative to the backend workspace (/app in the unified image).
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()  # 1. Runs when backend boots up
    await preload_gemma_model()

    yield  # Application handles incoming HTTP requests

    # 2. Runs when backend stops (e.g., Ctrl+C or Docker shutdown)
    await unload_gemma_model()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Tactical FinSec Telemetry Routing Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
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


# Mount SPA last so /api/v1, /health, and /docs keep priority.
# html=True serves index.html for Angular client-side routes.
if STATIC_DIR.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(STATIC_DIR), html=True),
        name="static",
    )
