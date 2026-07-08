from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


PrimaryVector = Literal["CYBER", "FRAUD", "NONE"]
TelemetryStatus = Literal["PASSED", "ESCALATED"]


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TelemetryEvent(SQLModel, table=True):
    __tablename__ = "telemetry_events"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    timestamp: str = Field(default_factory=_utc_iso, index=True)
    source_ip: str = Field(index=True)
    request_path: str
    transaction_amount: float
    account_token: str
    risk_score: int = Field(ge=0, le=100, index=True)
    primary_vector: str
    status: str
    payload_metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON),
    )
    triage_narrative: str | None = None


class TelemetryTriageRequest(BaseModel):
    source_ip: str
    request_path: str
    transaction_amount: float
    account_token: str


class OllamaMessage(BaseModel):
    role: str = "assistant"
    content: str


class TelemetryTriageResponse(BaseModel):
    model: str
    created_at: str
    message: OllamaMessage
    done: bool = True
    telemetry: TelemetryEvent
