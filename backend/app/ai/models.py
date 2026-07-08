from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class OllamaChatMessage(BaseModel):
    """Native Ollama /api/chat message shape (Gemma 4 may include thinking)."""

    role: str = "assistant"
    content: str = ""
    thinking: str | None = None
    reasoning: str | None = None

    model_config = {"extra": "ignore"}


class OllamaChatResponse(BaseModel):
    """Raw Ollama /api/chat non-streaming response envelope."""

    model: str
    created_at: str | None = None
    message: OllamaChatMessage
    done: bool = True
    done_reason: str | None = None
    total_duration: int | None = None
    load_duration: int | None = None
    prompt_eval_count: int | None = None
    prompt_eval_duration: int | None = None
    eval_count: int | None = None
    eval_duration: int | None = None

    model_config = {"extra": "ignore"}


class GemmaTriageResult(BaseModel):
    """Normalized FinSec triage JSON required from Gemma."""

    risk_score: int = Field(ge=0, le=100)
    status: Literal["PASSED", "ESCALATED"]
    primary_vector: Literal["CYBER", "FRAUD", "NORMAL"]
    triage_narrative: str = Field(min_length=1, max_length=200)

    model_config = {"extra": "ignore"}

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Any) -> str:
        if isinstance(value, str):
            return value.strip().upper()
        raise ValueError("status must be a string")

    @field_validator("primary_vector", mode="before")
    @classmethod
    def normalize_vector(cls, value: Any) -> str:
        if isinstance(value, str):
            return value.strip().upper()
        raise ValueError("primary_vector must be a string")

    @field_validator("triage_narrative", mode="before")
    @classmethod
    def normalize_narrative(cls, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("triage_narrative is required")
        return value.strip()[:200]

    @field_validator("risk_score", mode="before")
    @classmethod
    def normalize_score(cls, value: Any) -> int:
        score = int(value)
        return max(0, min(100, score))
