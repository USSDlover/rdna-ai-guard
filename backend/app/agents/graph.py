import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import antifraud_node, cybersec_node, synthesizer_node
from app.agents.state import TriageState

logger = logging.getLogger(__name__)

_compiled_graph = None


def build_escalation_graph():
    workflow = StateGraph(TriageState)

    workflow.add_node("cybersec", cybersec_node)
    workflow.add_node("antifraud", antifraud_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # Fan-out: both specialists start from START in parallel.
    workflow.add_edge(START, "cybersec")
    workflow.add_edge(START, "antifraud")

    # Fan-in: synthesizer waits for both specialist nodes.
    workflow.add_edge("cybersec", "synthesizer")
    workflow.add_edge("antifraud", "synthesizer")
    workflow.add_edge("synthesizer", END)

    return workflow.compile()


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_escalation_graph()
        logger.info("LangGraph escalation workflow compiled.")
    return _compiled_graph


def build_initial_state(
    telemetry_data: dict[str, Any],
    local_triage: dict[str, Any],
) -> TriageState:
    local_score = int(local_triage.get("risk_score", 0))
    local_status = str(local_triage.get("status", "PASSED")).upper()

    return TriageState(
        telemetry_data=telemetry_data,
        local_triage=local_triage,
        cyber_analysis=None,
        cyber_score=0,
        fraud_analysis=None,
        fraud_score=0,
        synthesized_narrative=None,
        final_risk_score=local_score,
        final_status=local_status if local_status in {"PASSED", "ESCALATED"} else "PASSED",
    )


async def run_escalation_analysis(
    telemetry_data: dict[str, Any],
    local_triage: dict[str, Any],
) -> TriageState:
    graph = get_compiled_graph()
    initial_state = build_initial_state(telemetry_data, local_triage)
    result = await graph.ainvoke(initial_state)
    return result
