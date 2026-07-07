import asyncio
import json
import random
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.models.schemas import (
    OllamaMessage,
    PrimaryVector,
    TelemetryEvent,
    TelemetryStatus,
    TelemetryTriageRequest,
    TelemetryTriageResponse,
)

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])

DANGEROUS_IP_PREFIXES: tuple[str, ...] = (
    "10.0.0.",
    "45.33.",
    "185.",
    "203.0.113.",
    "198.51.100.",
)

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


def _assess_risk(
    source_ip: str,
    transaction_amount: float,
) -> tuple[int, PrimaryVector, TelemetryStatus]:
    risk_score = 8
    primary_vector: PrimaryVector = "NONE"
    status: TelemetryStatus = "PASSED"

    if transaction_amount > 5000:
        excess = transaction_amount - 5000
        risk_score = min(100, 62 + int(excess / 250))
        primary_vector = "FRAUD"
        status = "ESCALATED"

    if source_ip.startswith(DANGEROUS_IP_PREFIXES):
        risk_score = max(risk_score, 88)
        primary_vector = "CYBER" if primary_vector == "NONE" else primary_vector
        status = "ESCALATED"

    if transaction_amount > 10000 and source_ip.startswith(DANGEROUS_IP_PREFIXES):
        risk_score = 97
        primary_vector = "FRAUD"
        status = "ESCALATED"

    return risk_score, primary_vector, status


def _build_routing_narrative(
    risk_score: int,
    primary_vector: PrimaryVector,
    status: TelemetryStatus,
    source_ip: str,
    transaction_amount: float,
) -> str:
    if status == "PASSED":
        return (
            f"Telemetry triage complete. Transaction from {source_ip} for "
            f"${transaction_amount:,.2f} assessed as low risk (score {risk_score}). "
            "Route to standard ingestion pipeline. No escalation required."
        )

    vector_label = "cyber-intrusion" if primary_vector == "CYBER" else "financial fraud"
    return (
        f"ESCALATION REQUIRED: {vector_label.upper()} indicators detected from {source_ip}. "
        f"Amount ${transaction_amount:,.2f}, composite risk score {risk_score}/100. "
        "Recommend immediate SOC handoff and transaction hold."
    )


def _build_telemetry_event(
    *,
    source_ip: str,
    request_path: str,
    transaction_amount: float,
    account_token: str,
) -> TelemetryEvent:
    risk_score, primary_vector, status = _assess_risk(source_ip, transaction_amount)
    return TelemetryEvent(
        id=str(uuid4()),
        timestamp=_utc_iso(),
        source_ip=source_ip,
        request_path=request_path,
        transaction_amount=transaction_amount,
        account_token=account_token,
        risk_score=risk_score,
        primary_vector=primary_vector,
        status=status,
    )


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


async def _telemetry_event_stream():
    sequence = 0
    while True:
        if sequence % 4 == 3:
            event = _build_spike_event(sequence)
        else:
            event = _build_clean_event(sequence)

        payload = event.model_dump_json()
        yield f"event: telemetry\ndata: {payload}\n\n"

        sequence += 1
        await asyncio.sleep(random.uniform(1.0, 2.0))


@router.post("/triage", response_model=TelemetryTriageResponse)
async def triage_telemetry(payload: TelemetryTriageRequest) -> TelemetryTriageResponse:
    telemetry = _build_telemetry_event(
        source_ip=payload.source_ip,
        request_path=payload.request_path,
        transaction_amount=payload.transaction_amount,
        account_token=payload.account_token,
    )

    narrative = _build_routing_narrative(
        risk_score=telemetry.risk_score,
        primary_vector=telemetry.primary_vector,
        status=telemetry.status,
        source_ip=telemetry.source_ip,
        transaction_amount=telemetry.transaction_amount,
    )

    return TelemetryTriageResponse(
        model=settings.GEMMA_MODEL,
        created_at=_utc_iso(),
        message=OllamaMessage(role="assistant", content=narrative),
        done=True,
        telemetry=telemetry,
    )


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
