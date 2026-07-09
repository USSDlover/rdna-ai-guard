"""
AI-301 Integration Diagnostic Suite
Mocks Ollama responses to verify parsing, fallback, triage routing,
PostgreSQL persistence hooks, and SSE broadcast wiring.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import unittest
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi.testclient import TestClient

from app.ai.models import GemmaTriageResult, OllamaChatResponse
from app.ai.ollama_client import (
    FALLBACK_TRIAGE,
    OLLAMA_TIMEOUT_SECONDS,
    extract_triage_candidates,
    preload_gemma_model,
    resolve_triage_from_ollama,
    run_gemma_triage,
    unload_gemma_model,
)
from app.core.config import settings
from app.core.events import broadcast_manager
from app.main import app, lifespan
from app.models.schemas import TelemetryEvent, TelemetryTriageRequest


VALID_TRIAGE_JSON = {
    "risk_score": 85,
    "status": "ESCALATED",
    "primary_vector": "FRAUD",
    "triage_narrative": "High-value transaction on auth endpoint. Potential ATO.",
}

SAMPLE_INCOMPLETE_CONTENT = {
    "model": "gemma4:12b",
    "created_at": "2026-07-08T15:11:57.722486466Z",
    "message": {
        "role": "assistant",
        "content": '{"risk_score": 45, "status": "ESCALATED", "status_code": 102}',
        "thinking": (
            "```json\n"
            + json.dumps(VALID_TRIAGE_JSON, indent=2)
            + "\n```"
        ),
    },
    "done": True,
    "done_reason": "stop",
}

SAMPLE_VALID_CONTENT = {
    "model": "gemma4:12b",
    "message": {
        "role": "assistant",
        "content": json.dumps(VALID_TRIAGE_JSON),
    },
    "done": True,
}


def _mock_httpx_response(status_code: int, payload: dict[str, Any] | None = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.text = json.dumps(payload or {})
    response.json.return_value = payload or {}
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error",
            request=MagicMock(),
            response=response,
        )
    return response


class StaticWiringChecks(unittest.TestCase):
  def test_lifespan_registers_preload_and_unload(self) -> None:
    source = inspect.getsource(lifespan)
    self.assertIn("preload_gemma_model", source)
    self.assertIn("unload_gemma_model", source)
    self.assertIn("init_db", source)

  def test_main_attaches_lifespan(self) -> None:
    self.assertIsNotNone(app.router.lifespan_context)

  def test_ollama_timeout_is_120_seconds(self) -> None:
    self.assertEqual(OLLAMA_TIMEOUT_SECONDS, 120.0)

  def test_run_gemma_triage_targets_api_chat(self) -> None:
    source = inspect.getsource(run_gemma_triage)
    self.assertIn("/api/chat", source)
    self.assertIn('"format": "json"', source)
    self.assertIn('"temperature": 0.0', source)
    self.assertIn('"num_predict": 1000', source)
    self.assertIn('"think": False', source)

  def test_preload_uses_keep_alive_minus_one(self) -> None:
    source = inspect.getsource(preload_gemma_model)
    self.assertIn('"keep_alive": -1', source)
    self.assertIn("settings.GEMMA_MODEL", source)

  def test_unload_uses_keep_alive_zero(self) -> None:
    source = inspect.getsource(unload_gemma_model)
    self.assertIn('"keep_alive": 0', source)


class ParsingResilienceTests(unittest.TestCase):
  def test_valid_content_payload_parses(self) -> None:
    response = OllamaChatResponse.model_validate(SAMPLE_VALID_CONTENT)
    triage = resolve_triage_from_ollama(response)
    self.assertIsNotNone(triage)
    assert triage is not None
    self.assertEqual(triage.risk_score, 85)
    self.assertEqual(triage.primary_vector, "FRAUD")

  def test_incomplete_content_falls_back_to_thinking_json(self) -> None:
    response = OllamaChatResponse.model_validate(SAMPLE_INCOMPLETE_CONTENT)
    triage = resolve_triage_from_ollama(response)
    self.assertIsNotNone(triage)
    assert triage is not None
    self.assertEqual(triage.risk_score, 85)
    self.assertIn("ATO", triage.triage_narrative)

  def test_malformed_payload_returns_no_candidates(self) -> None:
    candidates = extract_triage_candidates("not json at all")
    self.assertEqual(candidates, [])

  def test_empty_content_and_thinking_returns_none(self) -> None:
    response = OllamaChatResponse.model_validate(
      {
        "model": "gemma4:12b",
        "message": {"role": "assistant", "content": "", "thinking": ""},
        "done": True,
      }
    )
    self.assertIsNone(resolve_triage_from_ollama(response))


class AsyncOllamaClientTests(unittest.IsolatedAsyncioTestCase):
  async def test_network_failure_returns_fallback(self) -> None:
    with patch("app.ai.ollama_client.httpx.AsyncClient") as mock_client_cls:
      mock_client = AsyncMock()
      mock_client.__aenter__.return_value = mock_client
      mock_client.post.side_effect = httpx.ConnectError("connection refused")
      mock_client_cls.return_value = mock_client

      result = await run_gemma_triage({"source_ip": "1.1.1.1"})
      self.assertEqual(result, FALLBACK_TRIAGE.model_dump())

  async def test_timeout_returns_fallback(self) -> None:
    with patch("app.ai.ollama_client.httpx.AsyncClient") as mock_client_cls:
      mock_client = AsyncMock()
      mock_client.__aenter__.return_value = mock_client
      mock_client.post.side_effect = httpx.ReadTimeout("timeout")
      mock_client_cls.return_value = mock_client

      result = await run_gemma_triage({"source_ip": "1.1.1.1"})
      self.assertEqual(result["triage_narrative"], "Fallback: Local LLM unreachable")

  async def test_successful_ollama_response_parsed(self) -> None:
    with patch("app.ai.ollama_client.httpx.AsyncClient") as mock_client_cls:
      mock_client = AsyncMock()
      mock_client.__aenter__.return_value = mock_client
      mock_client.post.return_value = _mock_httpx_response(200, SAMPLE_VALID_CONTENT)
      mock_client_cls.return_value = mock_client

      result = await run_gemma_triage(
        {
          "source_ip": "185.220.101.42",
          "request_path": "/api/v1/auth/login",
          "transaction_amount": 12500.0,
          "account_token": "acct_****4821",
        }
      )
      self.assertEqual(result["risk_score"], 85)
      self.assertEqual(result["status"], "ESCALATED")

      called_kwargs = mock_client.post.call_args.kwargs
      self.assertIn("json", called_kwargs)
      self.assertEqual(called_kwargs["json"]["format"], "json")
      self.assertEqual(called_kwargs["json"]["options"]["temperature"], 0.0)
      self.assertEqual(called_kwargs["json"]["options"]["num_predict"], 1000)
      self.assertTrue(
        mock_client.post.call_args.args[0].startswith(
          f"{settings.OLLAMA_HOST.rstrip('/')}/api/chat"
        )
      )

  async def test_preload_posts_keep_alive_minus_one(self) -> None:
    with patch("app.ai.ollama_client.httpx.AsyncClient") as mock_client_cls:
      mock_client = AsyncMock()
      mock_client.__aenter__.return_value = mock_client
      mock_client.post.return_value = _mock_httpx_response(200, {"status": "ok"})
      mock_client_cls.return_value = mock_client

      await preload_gemma_model()
      body = mock_client.post.call_args.kwargs["json"]
      self.assertEqual(body["model"], settings.GEMMA_MODEL)
      self.assertEqual(body["keep_alive"], -1)

  async def test_unload_posts_keep_alive_zero(self) -> None:
    with patch("app.ai.ollama_client.httpx.AsyncClient") as mock_client_cls:
      mock_client = AsyncMock()
      mock_client.__aenter__.return_value = mock_client
      mock_client.post.return_value = _mock_httpx_response(200, {"status": "ok"})
      mock_client_cls.return_value = mock_client

      await unload_gemma_model()
      body = mock_client.post.call_args.kwargs["json"]
      self.assertEqual(body["keep_alive"], 0)


class TriagePipelineIntegrationTests(unittest.IsolatedAsyncioTestCase):
  async def test_triage_persists_and_broadcasts(self) -> None:
    mock_session = AsyncMock()
    captured_event: dict[str, TelemetryEvent] = {}

    async def fake_save(event: TelemetryEvent, session: AsyncMock) -> TelemetryEvent:
      captured_event["event"] = event
      return event

    queue = await broadcast_manager.subscribe()
    received: list[TelemetryEvent] = []

    async def collect_events() -> None:
      event = await asyncio.wait_for(queue.get(), timeout=2.0)
      received.append(event)

    collector = asyncio.create_task(collect_events())

    triage_payload = {
      "source_ip": "185.220.101.42",
      "request_path": "/api/v1/auth/login",
      "transaction_amount": 12500.0,
      "account_token": "acct_****4821",
    }

    with (
      patch("app.network.router.run_gemma_triage", new_callable=AsyncMock) as mock_triage,
      patch("app.network.router.save_telemetry_event", side_effect=fake_save),
    ):
      mock_triage.return_value = VALID_TRIAGE_JSON

      from app.network.router import triage_telemetry

      response = await triage_telemetry(
        payload=TelemetryTriageRequest(**triage_payload),
        session=mock_session,
      )

    await collector
    broadcast_manager.unsubscribe(queue)

    self.assertEqual(response.telemetry.risk_score, 85)
    self.assertEqual(response.telemetry.primary_vector, "FRAUD")
    self.assertEqual(response.telemetry.status, "ESCALATED")
    self.assertEqual(captured_event["event"].triage_narrative, VALID_TRIAGE_JSON["triage_narrative"])
    self.assertEqual(len(received), 1)
    self.assertEqual(received[0].risk_score, 85)

  async def test_sse_broadcast_manager_handles_multiple_subscribers(self) -> None:
    event = TelemetryEvent(
      source_ip="10.0.0.1",
      request_path="/api/v1/transfers",
      transaction_amount=100.0,
      account_token="acct_test",
      risk_score=90,
      primary_vector="FRAUD",
      status="ESCALATED",
    )

    queue_a = await broadcast_manager.subscribe()
    queue_b = await broadcast_manager.subscribe()

    await broadcast_manager.publish(event)

    self.assertEqual(await queue_a.get(), event)
    self.assertEqual(await queue_b.get(), event)

    broadcast_manager.unsubscribe(queue_a)
    broadcast_manager.unsubscribe(queue_b)


class FastAPILifespanSmokeTest(unittest.TestCase):
  def test_app_boot_and_shutdown_with_mocked_dependencies(self) -> None:
    with (
      patch("app.main.init_db", new_callable=AsyncMock) as mock_init_db,
      patch("app.main.preload_gemma_model", new_callable=AsyncMock) as mock_preload,
      patch("app.main.unload_gemma_model", new_callable=AsyncMock) as mock_unload,
    ):
      with TestClient(app) as client:
        health = client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ONLINE")

      mock_init_db.assert_awaited_once()
      mock_preload.assert_awaited_once()
      mock_unload.assert_awaited_once()


def run_suite() -> unittest.TestResult:
  loader = unittest.TestLoader()
  suite = unittest.TestSuite()
  suite.addTests(loader.loadTestsFromModule(__import__(__name__)))
  runner = unittest.TextTestRunner(verbosity=2)
  return runner.run(suite)


if __name__ == "__main__":
  result = run_suite()
  raise SystemExit(0 if result.wasSuccessful() else 1)
