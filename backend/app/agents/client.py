import json
import logging
import re
from typing import Any, Protocol

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"
FIREWORKS_TIMEOUT_SECONDS = 60.0


class LLMClient(Protocol):
    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]: ...


class FireworksClient:
    """Async OpenAI-compatible client for Fireworks AI inference."""

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        base_url: str = FIREWORKS_BASE_URL,
        timeout: float = FIREWORKS_TIMEOUT_SECONDS,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        request_body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 512,
            "response_format": {"type": "json_object"},
        }

        timeout = httpx.Timeout(
            connect=10.0,
            read=self._timeout,
            write=10.0,
            pool=10.0,
        )

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
            )
            response.raise_for_status()
            payload = response.json()

        content = payload["choices"][0]["message"]["content"]
        return _parse_json_content(content)


class MockFireworksClient:
    """Deterministic offline client used when FIREWORKS_API_KEY is unset."""

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        telemetry = _extract_telemetry_blob(user_prompt)
        source_ip = str(telemetry.get("source_ip", "0.0.0.0"))
        request_path = str(telemetry.get("request_path", "/"))
        amount = float(telemetry.get("transaction_amount", 0.0))

        if "CyberSec" in system_prompt or "cyber" in system_prompt.lower():
            score = 88 if "auth" in request_path or source_ip.startswith("185.") else 24
            return {
                "analysis": (
                    f"Mock cyber review: path={request_path}, source_ip={source_ip}. "
                    "Auth-route probing and non-residential IP indicators detected."
                ),
                "score": score,
            }

        if "Anti-Fraud" in system_prompt or "fraud" in system_prompt.lower():
            score = 92 if amount >= 5000 else 18
            return {
                "analysis": (
                    f"Mock fraud review: amount=${amount:,.2f}, token={telemetry.get('account_token')}. "
                    "High-value transfer velocity suggests potential mule routing."
                ),
                "score": score,
            }

        cyber_score = 88 if "auth" in request_path else 30
        fraud_score = 92 if amount >= 5000 else 20
        master_score = max(cyber_score, fraud_score)
        return {
            "synthesized_narrative": (
                f"MOCK CLOUD SYNTHESIS: Cyber={cyber_score}/100, Fraud={fraud_score}/100. "
                f"Composite risk {master_score}. Recommend SOC review and transaction hold."
            ),
            "final_risk_score": master_score,
            "final_status": "ESCALATED" if master_score >= 60 else "PASSED",
        }


def get_llm_client() -> LLMClient:
    if settings.FIREWORKS_API_KEY.strip():
        return FireworksClient(
            api_key=settings.FIREWORKS_API_KEY,
            model=settings.FIREWORKS_MODEL,
        )

    logger.warning(
        "FIREWORKS_API_KEY is unset — using MockFireworksClient for cloud escalation."
    )
    return MockFireworksClient()


def _parse_json_content(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    parsed = json.loads(cleaned.strip())
    if not isinstance(parsed, dict):
        raise ValueError("LLM response JSON must be an object")
    return parsed


def _extract_telemetry_blob(user_prompt: str) -> dict[str, Any]:
    match = re.search(r"\{[\s\S]*\}", user_prompt)
    if not match:
        return {}

    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}

    if not isinstance(parsed, dict):
        return {}

    telemetry = parsed.get("telemetry")
    if isinstance(telemetry, dict):
        return telemetry

    return parsed
