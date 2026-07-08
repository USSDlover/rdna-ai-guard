import json
import logging
import re
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

OLLAMA_TIMEOUT_SECONDS = 15.0
NARRATIVE_MAX_LENGTH = 200

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

FALLBACK_TRIAGE: dict[str, Any] = {
    "risk_score": 5,
    "status": "PASSED",
    "primary_vector": "NORMAL",
    "triage_narrative": "Fallback: Local LLM unreachable",
}


async def preload_gemma_model() -> None:
    """Preloads the Gemma model into VRAM/RAM and keeps it loaded indefinitely."""
    url = f"{settings.OLLAMA_HOST.rstrip('/')}/api/chat"
    body = {
        "model": settings.GEMMA_MODEL,
        "keep_alive": -1,  # -1 keeps model loaded until explicitly unloaded or daemon stops
    }

    logger.info(f"⏳ Preloading {settings.GEMMA_MODEL} into memory...")
    try:
        # 180s timeout allows slow disk-to-VRAM transfers on initial load
        timeout = httpx.Timeout(connect=10.0, read=180.0, write=10.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(url, json=body)
            if res.status_code == 200:
                logger.info(f"🚀 {settings.GEMMA_MODEL} successfully loaded and pinned in RAM/VRAM!")
            else:
                logger.warning(f"⚠️ Preload returned status {res.status_code}: {res.text}")
    except Exception as e:
        logger.error(f"❌ Failed to warm up model on startup: {e}")


async def unload_gemma_model() -> None:
    """Unloads the Gemma model from VRAM/RAM immediately upon application shutdown."""
    url = f"{settings.OLLAMA_HOST.rstrip('/')}/api/chat"
    body = {
        "model": settings.GEMMA_MODEL,
        "keep_alive": 0,  # 0 forces Ollama to evict model weights immediately
    }

    logger.info(f"🧹 Unloading {settings.GEMMA_MODEL} from VRAM/RAM...")
    try:
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(url, json=body)
            if res.status_code == 200:
                logger.info(f"✅ {settings.GEMMA_MODEL} successfully evicted from VRAM/RAM.")
            else:
                logger.warning(f"⚠️ Unload returned status {res.status_code}: {res.text}")
    except Exception as e:
        logger.error(f"❌ Failed to unload model during shutdown: {e}")


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
        "format": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.OLLAMA_HOST.rstrip('/')}/api/chat",
                json=request_body,
            )
            response.raise_for_status()
            response_payload = response.json()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("Ollama triage request failed: %s", exc)
        return dict(FALLBACK_TRIAGE)

    raw_content = _extract_response_content(response_payload)
    if not raw_content:
        logger.warning("Ollama triage response missing content: %s", response_payload)
        return dict(FALLBACK_TRIAGE)

    try:
        parsed = json.loads(_sanitize_json_response(raw_content))
    except json.JSONDecodeError as exc:
        logger.warning("Ollama triage JSON decode failed: %s | raw=%s", exc, raw_content)
        return dict(FALLBACK_TRIAGE)

    return _normalize_triage_result(parsed)


def _extract_response_content(response_payload: dict[str, Any]) -> str:
    message = response_payload.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content

    response_text = response_payload.get("response")
    if isinstance(response_text, str):
        return response_text

    return ""


def _sanitize_json_response(raw_text: str) -> str:
    cleaned = raw_text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    return cleaned.strip()


def _normalize_triage_result(parsed: Any) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        return dict(FALLBACK_TRIAGE)

    risk_score = _coerce_risk_score(parsed.get("risk_score"))
    status = _coerce_status(parsed.get("status"))
    primary_vector = _coerce_primary_vector(parsed.get("primary_vector"))
    triage_narrative = _coerce_narrative(parsed.get("triage_narrative"))

    return {
        "risk_score": risk_score,
        "status": status,
        "primary_vector": primary_vector,
        "triage_narrative": triage_narrative,
    }


def _coerce_risk_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return int(FALLBACK_TRIAGE["risk_score"])

    return max(0, min(100, score))


def _coerce_status(value: Any) -> str:
    if isinstance(value, str) and value.upper() == "ESCALATED":
        return "ESCALATED"
    return "PASSED"


def _coerce_primary_vector(value: Any) -> str:
    if not isinstance(value, str):
        return str(FALLBACK_TRIAGE["primary_vector"])

    normalized = value.upper()
    if normalized in {"CYBER", "FRAUD", "NORMAL"}:
        return normalized

    return str(FALLBACK_TRIAGE["primary_vector"])


def _coerce_narrative(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return str(FALLBACK_TRIAGE["triage_narrative"])

    return value.strip()[:NARRATIVE_MAX_LENGTH]
