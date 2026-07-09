import json
import logging
from typing import Any

from app.agents.client import LLMClient, get_llm_client
from app.agents.state import TriageState

logger = logging.getLogger(__name__)

CYBERSEC_SYSTEM_PROMPT = """You are Node A: CyberSec Specialist for RDNA AI Guard.

Analyze server paths, authentication routes, suspicious source IPs, protocol anomalies,
and credential-stuffing or intrusion indicators.

Respond ONLY with valid JSON:
{
  "analysis": "<concise structural cyber assessment>",
  "score": <integer 0-100>
}
"""

ANTIFRAUD_SYSTEM_PROMPT = """You are Node B: Anti-Fraud Specialist for RDNA AI Guard.

Analyze transaction amounts, routing anomalies, account token velocity patterns,
structuring behavior, and potential money-mule syndicate activity.

Respond ONLY with valid JSON:
{
  "analysis": "<concise financial fraud assessment>",
  "score": <integer 0-100>
}
"""

SYNTHESIZER_SYSTEM_PROMPT = """You are Node C: Synthesis & Routing Orchestrator for RDNA AI Guard.

Merge cyber and fraud specialist findings into a single operational verdict.

Respond ONLY with valid JSON:
{
  "synthesized_narrative": "<itemized diagnostic summary under 400 characters>",
  "final_risk_score": <integer 0-100>,
  "final_status": "PASSED" | "ESCALATED"
}
"""


def _clamp_score(value: Any, default: int = 0) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, min(100, score))


def _telemetry_context(state: TriageState) -> str:
    return json.dumps(
        {
            "telemetry": state["telemetry_data"],
            "local_triage": state["local_triage"],
        },
        separators=(",", ":"),
        sort_keys=True,
    )


async def cybersec_node(
    state: TriageState,
    *,
    client: LLMClient | None = None,
) -> dict[str, Any]:
    llm = client or get_llm_client()
    try:
        result = await llm.complete_json(
            system_prompt=CYBERSEC_SYSTEM_PROMPT,
            user_prompt=(
                "Perform cyber intrusion analysis for this telemetry packet:\n"
                f"{_telemetry_context(state)}"
            ),
        )
        return {
            "cyber_analysis": str(result.get("analysis", "No cyber analysis returned.")),
            "cyber_score": _clamp_score(result.get("score")),
        }
    except Exception as exc:
        logger.warning("CyberSec node failed, applying safe defaults: %s", exc)
        return {
            "cyber_analysis": "CyberSec node fallback: analysis unavailable.",
            "cyber_score": _clamp_score(state["local_triage"].get("risk_score"), 0),
        }


async def antifraud_node(
    state: TriageState,
    *,
    client: LLMClient | None = None,
) -> dict[str, Any]:
    llm = client or get_llm_client()
    try:
        result = await llm.complete_json(
            system_prompt=ANTIFRAUD_SYSTEM_PROMPT,
            user_prompt=(
                "Perform anti-fraud analysis for this telemetry packet:\n"
                f"{_telemetry_context(state)}"
            ),
        )
        return {
            "fraud_analysis": str(result.get("analysis", "No fraud analysis returned.")),
            "fraud_score": _clamp_score(result.get("score")),
        }
    except Exception as exc:
        logger.warning("Anti-Fraud node failed, applying safe defaults: %s", exc)
        return {
            "fraud_analysis": "Anti-Fraud node fallback: analysis unavailable.",
            "fraud_score": _clamp_score(state["local_triage"].get("risk_score"), 0),
        }


async def synthesizer_node(
    state: TriageState,
    *,
    client: LLMClient | None = None,
) -> dict[str, Any]:
    llm = client or get_llm_client()
    local_score = _clamp_score(state["local_triage"].get("risk_score"), 0)

    synthesis_input = {
        "telemetry": state["telemetry_data"],
        "local_triage": state["local_triage"],
        "cyber_analysis": state.get("cyber_analysis"),
        "cyber_score": state.get("cyber_score", 0),
        "fraud_analysis": state.get("fraud_analysis"),
        "fraud_score": state.get("fraud_score", 0),
    }

    try:
        result = await llm.complete_json(
            system_prompt=SYNTHESIZER_SYSTEM_PROMPT,
            user_prompt=(
                "Synthesize the specialist findings into a final routing verdict:\n"
                f"{json.dumps(synthesis_input, separators=(',', ':'), sort_keys=True)}"
            ),
        )
        final_score = _clamp_score(
            result.get("final_risk_score"),
            max(local_score, state.get("cyber_score", 0), state.get("fraud_score", 0)),
        )
        final_status = str(result.get("final_status", "ESCALATED")).upper()
        if final_status not in {"PASSED", "ESCALATED"}:
            final_status = "ESCALATED" if final_score >= 60 else "PASSED"

        return {
            "synthesized_narrative": str(
                result.get(
                    "synthesized_narrative",
                    "Cloud synthesis completed without narrative.",
                )
            )[:400],
            "final_risk_score": final_score,
            "final_status": final_status,
        }
    except Exception as exc:
        logger.warning("Synthesizer node failed, applying deterministic merge: %s", exc)
        cyber_score = state.get("cyber_score", 0)
        fraud_score = state.get("fraud_score", 0)
        final_score = max(local_score, cyber_score, fraud_score)
        return {
            "synthesized_narrative": (
                f"FALLBACK SYNTHESIS — Cyber {cyber_score}/100 | "
                f"Fraud {fraud_score}/100 | Local {local_score}/100."
            )[:400],
            "final_risk_score": final_score,
            "final_status": "ESCALATED" if final_score >= 60 else "PASSED",
        }
