from typing import Any, TypedDict


class TriageState(TypedDict):
    telemetry_data: dict[str, Any]
    local_triage: dict[str, Any]
    cyber_analysis: str | None
    cyber_score: int
    fraud_analysis: str | None
    fraud_score: int
    synthesized_narrative: str | None
    final_risk_score: int
    final_status: str
