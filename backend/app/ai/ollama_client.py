import json
import logging
import re
from typing import Any

import httpx
from pydantic import ValidationError

from app.ai.models import GemmaTriageResult, OllamaChatResponse
from app.core.config import settings

logger = logging.getLogger(__name__)

OLLAMA_TIMEOUT_SECONDS = 120.0

TRIAGE_SYSTEM_PROMPT = """You are a FinSec & Network Triage Analyst for RDNA AI Guard.

Evaluate inbound telemetry packets for financial fraud and cyber-intrusion risk.
Respond EXCLUSIVELY with valid JSON matching this schema:
{
  "risk_score": <integer 0-100>,
  "status": "PASSED" | "ESCALATED",
  "primary_vector": "CYBER" | "FRAUD" | "NORMAL",
  "triage_narrative": "<concise diagnostic string, max 200 characters>"
}

Rules:
- ESCALATED when risk_score >= 60 or clear threat indicators exist.
- CYBER for suspicious source IPs, auth probing, or intrusion patterns.
- FRAUD for abnormal transaction amounts, velocity, or structuring signals.
- NORMAL when no material threat is detected.
- triage_narrative must be factual, concise, and under 200 characters.
"""

FALLBACK_TRIAGE = GemmaTriageResult(
    risk_score=5,
    status="PASSED",
    primary_vector="NORMAL",
    triage_narrative="Fallback: Local LLM unreachable",
)

_JSON_OBJECT_PATTERN = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)


async def preload_gemma_model() -> None:
    """Preloads the Gemma model into VRAM/RAM and keeps it loaded indefinitely."""
    url = f"{settings.OLLAMA_HOST.rstrip('/')}/api/chat"
    body = {
        "model": settings.GEMMA_MODEL,
        "keep_alive": -1,
    }

    logger.info("Preloading %s into memory...", settings.GEMMA_MODEL)
    try:
        timeout = httpx.Timeout(connect=10.0, read=180.0, write=10.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(url, json=body)
            if res.status_code == 200:
                logger.info("%s successfully loaded and pinned in memory.", settings.GEMMA_MODEL)
            else:
                logger.warning("Preload returned status %s: %s", res.status_code, res.text)
    except Exception as exc:
        logger.error("Failed to warm up model on startup: %s", exc)


async def unload_gemma_model() -> None:
    """Unloads the Gemma model from VRAM/RAM immediately upon application shutdown."""
    url = f"{settings.OLLAMA_HOST.rstrip('/')}/api/chat"
    body = {
        "model": settings.GEMMA_MODEL,
        "keep_alive": 0,
    }

    logger.info("Unloading %s from memory...", settings.GEMMA_MODEL)
    try:
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(url, json=body)
            if res.status_code == 200:
                logger.info("%s successfully evicted from memory.", settings.GEMMA_MODEL)
            else:
                logger.warning("Unload returned status %s: %s", res.status_code, res.text)
    except Exception as exc:
        logger.error("Failed to unload model during shutdown: %s", exc)


async def run_gemma_triage(payload_metadata: dict[str, Any]) -> dict[str, Any]:
    prompt = (
        "Analyze this telemetry packet and return triage JSON only:\n"
        f"{json.dumps(payload_metadata, separators=(',', ':'), sort_keys=True)}"
    )

    request_body = {
        "model": settings.GEMMA_MODEL,
        "messages": [
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "think": False,
        "format": "json",
        "keep_alive": "10m",
        "options": {
            "temperature": 0.0,
            "num_predict": 1000,
        },
    }

    timeout = httpx.Timeout(
        connect=10.0,
        read=OLLAMA_TIMEOUT_SECONDS,
        write=10.0,
        pool=10.0,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{settings.OLLAMA_HOST.rstrip('/')}/api/chat",
                json=request_body,
            )
            response.raise_for_status()
            response_payload = response.json()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("Ollama triage request failed: %s", exc)
        return FALLBACK_TRIAGE.model_dump()

    try:
        chat_response = OllamaChatResponse.model_validate(response_payload)
    except ValidationError as exc:
        logger.warning("Ollama response schema mismatch: %s | payload=%s", exc, response_payload)
        return FALLBACK_TRIAGE.model_dump()

    triage = resolve_triage_from_ollama(chat_response)
    if triage is None:
        logger.warning(
            "Ollama triage missing valid result fields: content=%r thinking=%r",
            chat_response.message.content,
            (chat_response.message.thinking or "")[:500],
        )
        return FALLBACK_TRIAGE.model_dump()

    return triage.model_dump()


def resolve_triage_from_ollama(response: OllamaChatResponse) -> GemmaTriageResult | None:
    """
    Gemma 4 often returns incomplete JSON in `message.content` while the complete
    verdict sits inside a fenced JSON block in `message.thinking`.

    Prefer a fully valid content payload when present; otherwise extract from thinking.
    """
    message = response.message
    content_candidates = extract_triage_candidates(message.content)
    if content_candidates:
        return content_candidates[-1]

    thinking_text = "\n".join(
        part for part in (message.thinking, message.reasoning) if part
    )
    thinking_candidates = extract_triage_candidates(thinking_text)
    if thinking_candidates:
        return thinking_candidates[-1]

    return None


def extract_triage_candidates(raw_text: str | None) -> list[GemmaTriageResult]:
    if not raw_text or not raw_text.strip():
        return []

    results: list[GemmaTriageResult] = []
    for blob in iter_json_blobs(raw_text):
        try:
            parsed = json.loads(blob)
        except json.JSONDecodeError:
            continue

        try:
            results.append(GemmaTriageResult.model_validate(parsed))
        except ValidationError:
            continue

    return results


def iter_json_blobs(raw_text: str) -> list[str]:
    cleaned = raw_text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    blobs: list[str] = []

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            blobs.append(cleaned)
            return blobs
    except json.JSONDecodeError:
        pass

    for match in re.finditer(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw_text, flags=re.IGNORECASE):
        blobs.append(match.group(1).strip())

    for match in _JSON_OBJECT_PATTERN.finditer(raw_text):
        candidate = match.group(0).strip()
        if candidate not in blobs:
            blobs.append(candidate)

    return blobs
