import asyncio
import logging
import random
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import run_escalation_analysis
from app.ai.ollama_client import run_gemma_triage
from app.core.config import settings
from app.core.db import async_session_factory, get_async_session
from app.core.events import broadcast_manager
from app.models.schemas import (
    OllamaMessage,
    PrimaryVector,
    TelemetryEvent,
    TelemetryStatus,
    TelemetryTriageRequest,
    TelemetryTriageResponse,
)
from app.services.telemetry_service import (
    get_recent_telemetry,
    get_telemetry_event_by_id,
    save_telemetry_event,
    update_telemetry_event,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])

CLEAN_SOURCE_IPS: tuple[str, ...] = (
    "172.16.42.10",
    "192.168.1.105",
    "10.10.20.55",
    "203.0.113.12",
    "198.51.100.44",
)

MALICIOUS_SOURCE_IPS: tuple[str, ...] = (
    "45.33.12.88",
    "185.220.101.42",
    "10.0.0.77",
    "203.0.113.199",
)

REQUEST_PATHS: tuple[str, ...] = (
    "/api/v1/transfers",
    "/api/v1/auth/login",
    "/api/v1/payments/initiate",
    "/api/v1/accounts/balance",
    "/api/v1/cards/authorize",
)

ACCOUNT_TOKENS: tuple[str, ...] = (
    "acct_****4821",
    "acct_****9034",
    "acct_****1178",
    "acct_****6620",
    "acct_****3391",
)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _map_primary_vector(vector: str) -> PrimaryVector:
    if vector == "CYBER":
        return "CYBER"
    if vector == "FRAUD":
        return "FRAUD"
    return "NONE"


def _build_clean_event(sequence: int) -> TelemetryEvent:
    return TelemetryEvent(
        id=str(uuid4()),
        timestamp=_utc_iso(),
        source_ip=CLEAN_SOURCE_IPS[sequence % len(CLEAN_SOURCE_IPS)],
        request_path=REQUEST_PATHS[sequence % len(REQUEST_PATHS)],
        transaction_amount=round(random.uniform(12.50, 4800.00), 2),
        account_token=ACCOUNT_TOKENS[sequence % len(ACCOUNT_TOKENS)],
        risk_score=random.randint(3, 18),
        primary_vector="NONE",
        status="PASSED",
    )


def _build_spike_event(sequence: int) -> TelemetryEvent:
    is_cyber = sequence % 2 == 0
    if is_cyber:
        return TelemetryEvent(
            id=str(uuid4()),
            timestamp=_utc_iso(),
            source_ip=MALICIOUS_SOURCE_IPS[sequence % len(MALICIOUS_SOURCE_IPS)],
            request_path="/api/v1/auth/login",
            transaction_amount=0.0,
            account_token=ACCOUNT_TOKENS[sequence % len(ACCOUNT_TOKENS)],
            risk_score=random.randint(82, 96),
            primary_vector="CYBER",
            status="ESCALATED",
        )

    return TelemetryEvent(
        id=str(uuid4()),
        timestamp=_utc_iso(),
        source_ip=CLEAN_SOURCE_IPS[sequence % len(CLEAN_SOURCE_IPS)],
        request_path="/api/v1/transfers",
        transaction_amount=round(random.uniform(8500.00, 24999.99), 2),
        account_token=ACCOUNT_TOKENS[(sequence + 1) % len(ACCOUNT_TOKENS)],
        risk_score=random.randint(78, 99),
        primary_vector="FRAUD",
        status="ESCALATED",
    )


def _build_seed_event(sequence: int) -> TelemetryEvent:
    if sequence % 4 == 3:
        return _build_spike_event(sequence)
    return _build_clean_event(sequence)


async def _persist_and_broadcast(
    event: TelemetryEvent,
    session: AsyncSession,
    *,
    triage_narrative: str | None = None,
) -> TelemetryEvent:
    if triage_narrative is not None:
        event.triage_narrative = triage_narrative

    persisted = await save_telemetry_event(event, session)
    await broadcast_manager.publish(persisted)
    return persisted


def _resolve_primary_vector(cyber_score: int, fraud_score: int) -> PrimaryVector:
    if cyber_score == 0 and fraud_score == 0:
        return "NONE"
    if cyber_score >= fraud_score:
        return "CYBER"
    return "FRAUD"


async def _execute_cloud_escalation(
    event_id: str,
    telemetry_data: dict[str, object],
    local_triage: dict[str, object],
) -> None:
    logger.info("Starting cloud escalation workflow for event %s", event_id)

    try:
        final_state = await run_escalation_analysis(telemetry_data, local_triage)
    except Exception:
        logger.exception("Cloud escalation graph failed for event %s", event_id)
        return

    try:
        async with async_session_factory() as session:
            event = await get_telemetry_event_by_id(event_id, session)
            if event is None:
                logger.warning("Cloud escalation could not find event %s", event_id)
                return

            cyber_score = int(final_state.get("cyber_score", 0))
            fraud_score = int(final_state.get("fraud_score", 0))
            final_status: TelemetryStatus = (
                "ESCALATED"
                if str(final_state.get("final_status", "ESCALATED")).upper() == "ESCALATED"
                else "PASSED"
            )

            metadata = dict(event.payload_metadata or {})
            metadata["cloud_escalation"] = {
                "provider": "fireworks" if settings.FIREWORKS_API_KEY.strip() else "mock",
                "model": settings.FIREWORKS_MODEL,
                "cyber_analysis": final_state.get("cyber_analysis"),
                "cyber_score": cyber_score,
                "fraud_analysis": final_state.get("fraud_analysis"),
                "fraud_score": fraud_score,
                "synthesized_narrative": final_state.get("synthesized_narrative"),
            }

            event.triage_narrative = str(
                final_state.get("synthesized_narrative") or event.triage_narrative
            )
            event.risk_score = int(final_state.get("final_risk_score", event.risk_score))
            event.status = final_status
            event.primary_vector = _resolve_primary_vector(cyber_score, fraud_score)
            event.payload_metadata = metadata

            enriched = await update_telemetry_event(event, session)
            await broadcast_manager.publish(enriched)
            logger.info("Cloud escalation complete for event %s", event_id)
    except Exception:
        logger.exception("Cloud escalation persistence failed for event %s", event_id)


async def _replay_recent_events() -> list[TelemetryEvent]:
    async with async_session_factory() as session:
        recent_events = await get_recent_telemetry(session, limit=50)

    return list(reversed(recent_events))


async def _telemetry_event_stream():
    queue = await broadcast_manager.subscribe()

    try:
        for event in await _replay_recent_events():
            payload = event.model_dump_json()
            yield f"event: telemetry\ndata: {payload}\n\n"

        while True:
            event = await queue.get()
            payload = event.model_dump_json()
            yield f"event: telemetry\ndata: {payload}\n\n"
    except asyncio.CancelledError:
        raise
    finally:
        broadcast_manager.unsubscribe(queue)


@router.post("/triage", response_model=TelemetryTriageResponse)
async def triage_telemetry(
    payload: TelemetryTriageRequest,
    session: AsyncSession = Depends(get_async_session),
) -> TelemetryTriageResponse:
    payload_data = payload.model_dump()
    triage_result = await run_gemma_triage(payload_data)

    narrative = str(triage_result["triage_narrative"])
    primary_vector = _map_primary_vector(str(triage_result["primary_vector"]))
    status: TelemetryStatus = (
        "ESCALATED" if triage_result["status"] == "ESCALATED" else "PASSED"
    )

    telemetry = TelemetryEvent(
        id=str(uuid4()),
        timestamp=_utc_iso(),
        source_ip=payload.source_ip,
        request_path=payload.request_path,
        transaction_amount=payload.transaction_amount,
        account_token=payload.account_token,
        risk_score=int(triage_result["risk_score"]),
        primary_vector=primary_vector,
        status=status,
        payload_metadata=payload_data,
        triage_narrative=narrative,
    )

    persisted = await _persist_and_broadcast(telemetry, session)

    if persisted.status == "ESCALATED":
        asyncio.create_task(
            _execute_cloud_escalation(
                persisted.id,
                payload_data,
                triage_result,
            )
        )

    return TelemetryTriageResponse(
        model=settings.GEMMA_MODEL,
        created_at=_utc_iso(),
        message=OllamaMessage(role="assistant", content=narrative),
        done=True,
        telemetry=persisted,
    )


@router.post("/seed")
async def seed_telemetry(
    session: AsyncSession = Depends(get_async_session),
    count: int = Query(default=1, ge=1, le=20),
) -> dict[str, object]:
    seeded_events: list[TelemetryEvent] = []

    for sequence in range(count):
        event = _build_seed_event(sequence)
        persisted = await _persist_and_broadcast(event, session)
        seeded_events.append(persisted)

    return {
        "seeded": len(seeded_events),
        "events": seeded_events,
    }


@router.get("/stream")
async def stream_telemetry() -> StreamingResponse:
    return StreamingResponse(
        _telemetry_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
