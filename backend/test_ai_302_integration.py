"""
AI-302 Integration Diagnostic Suite
Verifies LangGraph escalation workflow, mock Fireworks client fallback,
and async router enrichment + SSE rebroadcast hooks.
"""

from __future__ import annotations

import asyncio
import inspect
import unittest
from typing import Any
from unittest.mock import AsyncMock, patch

from app.agents.client import MockFireworksClient, get_llm_client
from app.agents.graph import build_escalation_graph, run_escalation_analysis
from app.agents.nodes import antifraud_node, cybersec_node, synthesizer_node
from app.agents.state import TriageState
from app.core.config import settings
from app.core.events import broadcast_manager
from app.models.schemas import TelemetryEvent, TelemetryTriageRequest
from app.network.router import _execute_cloud_escalation


TELEMETRY_DATA = {
    "source_ip": "185.220.101.42",
    "request_path": "/api/v1/auth/login",
    "transaction_amount": 18500.0,
    "account_token": "acct_****4821",
}

LOCAL_TRIAGE = {
    "risk_score": 85,
    "status": "ESCALATED",
    "primary_vector": "FRAUD",
    "triage_narrative": "Local Gemma escalation.",
}


class StaticWiringChecks(unittest.TestCase):
    def test_config_exposes_fireworks_settings(self) -> None:
        self.assertTrue(hasattr(settings, "FIREWORKS_API_KEY"))
        self.assertTrue(hasattr(settings, "FIREWORKS_MODEL"))
        self.assertEqual(
            settings.FIREWORKS_MODEL,
            "accounts/fireworks/models/llama-v3p1-70b-instruct",
        )

    def test_router_triggers_background_escalation(self) -> None:
        source = inspect.getsource(
            __import__("app.network.router", fromlist=["triage_telemetry"]).triage_telemetry
        )
        self.assertIn("_execute_cloud_escalation", source)
        self.assertIn("asyncio.create_task", source)
        self.assertIn('persisted.status == "ESCALATED"', source)

    def test_graph_compiles(self) -> None:
        graph = build_escalation_graph()
        self.assertIsNotNone(graph)


class MockClientNodeTests(unittest.IsolatedAsyncioTestCase):
    async def test_cybersec_node_returns_score(self) -> None:
        state = TriageState(
            telemetry_data=TELEMETRY_DATA,
            local_triage=LOCAL_TRIAGE,
            cyber_analysis=None,
            cyber_score=0,
            fraud_analysis=None,
            fraud_score=0,
            synthesized_narrative=None,
            final_risk_score=85,
            final_status="ESCALATED",
        )
        result = await cybersec_node(state, client=MockFireworksClient())
        self.assertGreaterEqual(result["cyber_score"], 60)
        self.assertIn("mock cyber review", result["cyber_analysis"].lower())

    async def test_antifraud_node_returns_score(self) -> None:
        state = TriageState(
            telemetry_data=TELEMETRY_DATA,
            local_triage=LOCAL_TRIAGE,
            cyber_analysis=None,
            cyber_score=0,
            fraud_analysis=None,
            fraud_score=0,
            synthesized_narrative=None,
            final_risk_score=85,
            final_status="ESCALATED",
        )
        result = await antifraud_node(state, client=MockFireworksClient())
        self.assertGreaterEqual(result["fraud_score"], 60)
        self.assertIn("fraud", result["fraud_analysis"].lower())

    async def test_synthesizer_node_merges_scores(self) -> None:
        state = TriageState(
            telemetry_data=TELEMETRY_DATA,
            local_triage=LOCAL_TRIAGE,
            cyber_analysis="Cyber alert",
            cyber_score=88,
            fraud_analysis="Fraud alert",
            fraud_score=92,
            synthesized_narrative=None,
            final_risk_score=85,
            final_status="ESCALATED",
        )
        result = await synthesizer_node(state, client=MockFireworksClient())
        self.assertGreaterEqual(result["final_risk_score"], 60)
        self.assertEqual(result["final_status"], "ESCALATED")
        self.assertTrue(result["synthesized_narrative"])


class GraphWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_graph_runs_with_mock_client(self) -> None:
        with patch("app.agents.nodes.get_llm_client", return_value=MockFireworksClient()):
            final_state = await run_escalation_analysis(TELEMETRY_DATA, LOCAL_TRIAGE)

        self.assertIsNotNone(final_state.get("cyber_analysis"))
        self.assertIsNotNone(final_state.get("fraud_analysis"))
        self.assertIsNotNone(final_state.get("synthesized_narrative"))
        self.assertGreaterEqual(final_state["final_risk_score"], 60)
        self.assertEqual(final_state["final_status"], "ESCALATED")

    def test_get_llm_client_uses_mock_without_api_key(self) -> None:
        with patch.object(settings, "FIREWORKS_API_KEY", ""):
            client = get_llm_client()
        self.assertIsInstance(client, MockFireworksClient)


class EscalationPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_cloud_escalation_updates_db_and_broadcasts(self) -> None:
        event = TelemetryEvent(
            id="event-302-test",
            source_ip=TELEMETRY_DATA["source_ip"],
            request_path=TELEMETRY_DATA["request_path"],
            transaction_amount=TELEMETRY_DATA["transaction_amount"],
            account_token=TELEMETRY_DATA["account_token"],
            risk_score=85,
            primary_vector="FRAUD",
            status="ESCALATED",
            payload_metadata=TELEMETRY_DATA,
            triage_narrative="Initial local narrative",
        )

        queue = await broadcast_manager.subscribe()
        received: list[TelemetryEvent] = []

        async def collect() -> None:
            received.append(await asyncio.wait_for(queue.get(), timeout=3.0))

        collector = asyncio.create_task(collect())

        final_state = {
            "cyber_analysis": "Credential stuffing on auth route.",
            "cyber_score": 88,
            "fraud_analysis": "High-value transfer anomaly.",
            "fraud_score": 94,
            "synthesized_narrative": "CLOUD: ATO + mule routing confirmed. Hold funds.",
            "final_risk_score": 94,
            "final_status": "ESCALATED",
        }

        with (
            patch(
                "app.network.router.run_escalation_analysis",
                new_callable=AsyncMock,
                return_value=final_state,
            ),
            patch(
                "app.network.router.get_telemetry_event_by_id",
                new_callable=AsyncMock,
                return_value=event,
            ) as mock_get,
            patch(
                "app.network.router.update_telemetry_event",
                new_callable=AsyncMock,
                side_effect=lambda updated, _session: updated,
            ) as mock_update,
        ):
            await _execute_cloud_escalation(
                event.id,
                TELEMETRY_DATA,
                LOCAL_TRIAGE,
            )

        await collector
        broadcast_manager.unsubscribe(queue)

        mock_get.assert_awaited_once()
        mock_update.assert_awaited_once()
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].risk_score, 94)
        self.assertIn("CLOUD", received[0].triage_narrative or "")


class TriageEscalationHookTests(unittest.IsolatedAsyncioTestCase):
    async def test_escalated_triage_schedules_background_task(self) -> None:
        mock_session = AsyncMock()
        triage_payload = TelemetryTriageRequest(**TELEMETRY_DATA)

        with (
            patch(
                "app.network.router.run_gemma_triage",
                new_callable=AsyncMock,
                return_value=LOCAL_TRIAGE,
            ),
            patch(
                "app.network.router.save_telemetry_event",
                new_callable=AsyncMock,
                side_effect=lambda event, _session: event,
            ),
            patch("app.network.router.asyncio.create_task") as mock_create_task,
            patch("app.network.router.broadcast_manager.publish", new_callable=AsyncMock),
        ):
            from app.network.router import triage_telemetry

            response = await triage_telemetry(payload=triage_payload, session=mock_session)

        self.assertEqual(response.telemetry.status, "ESCALATED")
        mock_create_task.assert_called_once()
        scheduled_coro = mock_create_task.call_args.args[0]
        self.assertTrue(asyncio.iscoroutine(scheduled_coro))
        scheduled_coro.close()


def run_suite() -> unittest.TestResult:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(__import__(__name__)))
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    result = run_suite()
    raise SystemExit(0 if result.wasSuccessful() else 1)
