from typing import Literal

from pydantic import BaseModel, Field


PrimaryVector = Literal["CYBER", "FRAUD", "NONE"]
TelemetryStatus = Literal["PASSED", "ESCALATED"]


class TelemetryEvent(BaseModel):
    id: str
    timestamp: str
    source_ip: str
    request_path: str
    transaction_amount: float
    account_token: str
    risk_score: int = Field(ge=0, le=100)
    primary_vector: PrimaryVector
    status: TelemetryStatus


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
