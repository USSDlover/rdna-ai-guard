#!/usr/bin/env python3
"""
RDNA AI Guard — Cloud Multi-Agent Escalation Test Suite (AI-302)

Validates the LangGraph CyberSec ∥ Anti-Fraud → Synthesizer pipeline fires on
ESCALATED triage events and enriches records via Fireworks AI (or mock fallback).

Test modes:
  graph  — Direct LangGraph invocation (fast, no Ollama / no HTTP)
  api    — Full POST /telemetry/triage + SSE enrichment watch (end-to-end)
  all    — Both modes (default)

Usage (from backend/):
  python -m app.scripts.test_cloud_escalation
  python -m app.scripts.test_cloud_escalation --mode api --require-fireworks
  python -m app.scripts.test_cloud_escalation --mode graph
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.agents.client import FireworksClient, MockFireworksClient, get_llm_client
from app.agents.graph import run_escalation_analysis
from app.core.config import settings

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
API_PREFIX = "/api/v1"
TRIAGE_TIMEOUT = httpx.Timeout(connect=15.0, read=180.0, write=15.0, pool=15.0)

CYBER_SCENARIO = {
    "name": "Cyber intrusion escalation",
    "vector": "CYBER",
    "payload": {
        "source_ip": "45.33.12.88",
        "request_path": "/api/v1/auth/login",
        "transaction_amount": 0.0,
        "account_token": "acct_****4821",
    },
    "local_triage": {
        "risk_score": 91,
        "status": "ESCALATED",
        "primary_vector": "CYBER",
        "triage_narrative": "Local Gemma: credential-stuffing on auth endpoint.",
    },
}

FRAUD_SCENARIO = {
    "name": "Financial fraud escalation",
    "vector": "FRAUD",
    "payload": {
        "source_ip": "10.10.20.55",
        "request_path": "/api/v1/transfers",
        "transaction_amount": 22499.99,
        "account_token": "acct_****6620",
    },
    "local_triage": {
        "risk_score": 88,
        "status": "ESCALATED",
        "primary_vector": "FRAUD",
        "triage_narrative": "Local Gemma: high-value cross-border transfer anomaly.",
    },
}


@dataclass
class ScenarioResult:
    name: str
    vector: str
    passed: bool = False
    provider: str = "unknown"
    cyber_score: int | None = None
    fraud_score: int | None = None
    narrative: str = ""
    errors: list[str] = field(default_factory=list)


@dataclass
class TestReport:
    llm_client: str = "unknown"
    fireworks_configured: bool = False
    graph_results: list[ScenarioResult] = field(default_factory=list)
    api_results: list[ScenarioResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        results = self.graph_results + self.api_results
        return bool(results) and all(result.passed for result in results)


def _banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def _client_label() -> str:
    client = get_llm_client()
    if isinstance(client, FireworksClient):
        return f"FireworksClient ({settings.FIREWORKS_MODEL})"
    if isinstance(client, MockFireworksClient):
        return "MockFireworksClient (offline)"
    return type(client).__name__


def _validate_escalation_state(
    state: dict[str, Any],
    *,
    scenario_name: str,
    require_fireworks: bool,
    provider: str,
) -> ScenarioResult:
    result = ScenarioResult(name=scenario_name, vector="", provider=provider)

    cyber_score = state.get("cyber_score")
    fraud_score = state.get("fraud_score")
    narrative = str(state.get("synthesized_narrative") or "")
    cyber_analysis = str(state.get("cyber_analysis") or "")
    fraud_analysis = str(state.get("fraud_analysis") or "")

    result.cyber_score = int(cyber_score) if cyber_score is not None else None
    result.fraud_score = int(fraud_score) if fraud_score is not None else None
    result.narrative = narrative

    if not cyber_analysis:
        result.errors.append("missing cyber_analysis from CyberSec node")
    if not fraud_analysis:
        result.errors.append("missing fraud_analysis from Anti-Fraud node")
    if result.cyber_score is None or result.cyber_score < 1:
        result.errors.append(f"invalid cyber_score: {cyber_score}")
    if result.fraud_score is None or result.fraud_score < 1:
        result.errors.append(f"invalid fraud_score: {fraud_score}")
    if not narrative:
        result.errors.append("missing synthesized_narrative from Synthesizer node")
    if str(state.get("final_status", "")).upper() != "ESCALATED":
        result.errors.append(f"expected final_status=ESCALATED, got {state.get('final_status')}")

    if require_fireworks and provider != "fireworks":
        result.errors.append(
            "FIREWORKS_API_KEY not configured — backend is using mock cloud agent"
        )
    if provider == "mock" and "MOCK CLOUD SYNTHESIS" in narrative.upper():
        result.errors.append("mock synthesis detected (set FIREWORKS_API_KEY for live cloud)")

    result.passed = not result.errors
    return result


async def run_graph_scenario(scenario: dict[str, Any], require_fireworks: bool) -> ScenarioResult:
    print(f"\n  -> Graph test: {scenario['name']} [{scenario['vector']}]")
    provider = "fireworks" if settings.FIREWORKS_API_KEY.strip() else "mock"

    try:
        state = await run_escalation_analysis(scenario["payload"], scenario["local_triage"])
    except Exception as exc:
        result = ScenarioResult(
            name=scenario["name"],
            vector=scenario["vector"],
            provider=provider,
            errors=[f"LangGraph invocation failed: {exc}"],
        )
        return result

    result = _validate_escalation_state(
        state,
        scenario_name=scenario["name"],
        require_fireworks=require_fireworks,
        provider=provider,
    )
    result.vector = scenario["vector"]

    status = "PASS" if result.passed else "FAIL"
    print(f"     [{status}] provider={provider} cyber={result.cyber_score} fraud={result.fraud_score}")
    print(f"            narrative: {result.narrative[:100]}...")
    for error in result.errors:
        print(f"            - {error}")

    return result


async def collect_sse_events(
    base_url: str,
    stop_event: asyncio.Event,
    out_queue: asyncio.Queue[dict[str, Any]],
) -> None:
    url = f"{base_url.rstrip('/')}{API_PREFIX}/telemetry/stream"

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", url, timeout=None) as response:
                response.raise_for_status()
                event_name = ""
                async for raw_line in response.aiter_lines():
                    if stop_event.is_set():
                        break
                    if not raw_line:
                        continue
                    if raw_line.startswith("event:"):
                        event_name = raw_line.split(":", 1)[1].strip()
                        continue
                    if event_name != "telemetry" or not raw_line.startswith("data:"):
                        continue
                    try:
                        payload = json.loads(raw_line.split(":", 1)[1].strip())
                    except json.JSONDecodeError:
                        continue
                    await out_queue.put(payload)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        await out_queue.put({"__error__": str(exc)})


async def wait_for_cloud_enrichment(
    event_id: str,
    out_queue: asyncio.Queue[dict[str, Any]],
    timeout_seconds: float,
) -> dict[str, Any] | None:
    deadline = time.perf_counter() + timeout_seconds
    latest_match: dict[str, Any] | None = None

    while time.perf_counter() < deadline:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            break

        try:
            payload = await asyncio.wait_for(out_queue.get(), timeout=remaining)
        except asyncio.TimeoutError:
            break

        if "__error__" in payload:
            raise RuntimeError(str(payload["__error__"]))

        if str(payload.get("id")) != event_id:
            continue

        latest_match = payload
        cloud = (payload.get("payload_metadata") or {}).get("cloud_escalation")
        if cloud and cloud.get("synthesized_narrative"):
            return payload

    return latest_match


async def run_api_scenario(
    client: httpx.AsyncClient,
    scenario: dict[str, Any],
    *,
    require_fireworks: bool,
    enrichment_timeout: float,
) -> ScenarioResult:
    print(f"\n  -> API test: {scenario['name']} [{scenario['vector']}]")
    provider = "fireworks" if settings.FIREWORKS_API_KEY.strip() else "mock"
    result = ScenarioResult(name=scenario["name"], vector=scenario["vector"], provider=provider)

    stop_event = asyncio.Event()
    event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    collector = asyncio.create_task(
        collect_sse_events(str(client.base_url), stop_event, event_queue)
    )

    try:
        try:
            response = await client.post(
                f"{API_PREFIX}/telemetry/triage",
                json=scenario["payload"],
                timeout=TRIAGE_TIMEOUT,
            )
        except httpx.ReadTimeout:
            result.errors.append("triage request timed out (Ollama may still be loading)")
            return result
        except Exception as exc:
            result.errors.append(f"triage request failed: {exc}")
            return result

        if response.status_code != 200:
            result.errors.append(f"HTTP {response.status_code}: {response.text[:200]}")
            return result

        body = response.json()
        telemetry = body.get("telemetry", {})
        event_id = str(telemetry.get("id", ""))

        if telemetry.get("status") != "ESCALATED":
            result.errors.append(
                f"local triage was {telemetry.get('status')!r} — "
                "Ollama did not escalate; cloud loop was not triggered"
            )
            print(f"     [FAIL] Local status={telemetry.get('status')} - escalation skipped")
            for error in result.errors:
                print(f"            - {error}")
            return result

        print(f"     Local ESCALATED (id={event_id[:8]}...) - waiting for cloud enrichment...")

        enriched = await wait_for_cloud_enrichment(
            event_id,
            event_queue,
            enrichment_timeout,
        )
    finally:
        stop_event.set()
        collector.cancel()
        try:
            await collector
        except asyncio.CancelledError:
            pass

    if enriched is None:
        result.errors.append("timed out waiting for cloud_escalation SSE update")
        return result

    cloud = (enriched.get("payload_metadata") or {}).get("cloud_escalation") or {}
    provider = str(cloud.get("provider", provider))
    result.provider = provider

    graph_like_state = {
        "cyber_analysis": cloud.get("cyber_analysis"),
        "cyber_score": cloud.get("cyber_score"),
        "fraud_analysis": cloud.get("fraud_analysis"),
        "fraud_score": cloud.get("fraud_score"),
        "synthesized_narrative": cloud.get("synthesized_narrative")
        or enriched.get("triage_narrative"),
        "final_status": enriched.get("status"),
        "final_risk_score": enriched.get("risk_score"),
    }

    validated = _validate_escalation_state(
        graph_like_state,
        scenario_name=scenario["name"],
        require_fireworks=require_fireworks,
        provider=provider,
    )
    result.passed = validated.passed
    result.cyber_score = validated.cyber_score
    result.fraud_score = validated.fraud_score
    result.narrative = validated.narrative
    result.errors = validated.errors

    status = "PASS" if result.passed else "FAIL"
    print(f"     [{status}] provider={provider} cyber={result.cyber_score} fraud={result.fraud_score}")
    print(f"            vector={enriched.get('primary_vector')} risk={enriched.get('risk_score')}")
    print(f"            narrative: {result.narrative[:100]}...")
    for error in result.errors:
        print(f"            - {error}")

    return result


async def async_main(args: argparse.Namespace) -> int:
    report = TestReport()
    report.fireworks_configured = bool(settings.FIREWORKS_API_KEY.strip())
    report.llm_client = _client_label()

    _banner("RDNA AI Guard - Cloud Multi-Agent Escalation Test (AI-302)")
    print(f"  LLM client     : {report.llm_client}")
    print(f"  Fireworks key  : {'SET' if report.fireworks_configured else 'NOT SET (mock mode)'}")
    print(f"  Backend URL    : {args.base_url}")

    if args.require_fireworks and not report.fireworks_configured:
        print("\n  FAIL  --require-fireworks set but FIREWORKS_API_KEY is empty.")
        print("        Add FIREWORKS_API_KEY to backend/.env and restart the backend.")
        return 1

    scenarios = [CYBER_SCENARIO, FRAUD_SCENARIO]

    if args.mode in {"graph", "all"}:
        _banner("PHASE A - Direct LangGraph (CyberSec || Anti-Fraud -> Synthesizer)")
        for scenario in scenarios:
            result = await run_graph_scenario(scenario, args.require_fireworks)
            report.graph_results.append(result)

    if args.mode in {"api", "all"}:
        _banner("PHASE B - Live API triage + SSE cloud enrichment")
        print("  Requires: backend running, Ollama reachable, PostgreSQL up\n")

        async with httpx.AsyncClient(base_url=args.base_url.rstrip("/")) as client:
            try:
                health = await client.get("/health", timeout=10.0)
                health.raise_for_status()
                print(f"  Backend health: {health.json().get('status')}")
            except Exception as exc:
                print(f"  FAIL  Backend unreachable: {exc}")
                return 1

            for scenario in scenarios:
                result = await run_api_scenario(
                    client,
                    scenario,
                    require_fireworks=args.require_fireworks,
                    enrichment_timeout=args.enrichment_timeout,
                )
                report.api_results.append(result)
                await asyncio.sleep(args.delay)

    _banner("SUMMARY")
    for label, results in (
        ("Graph", report.graph_results),
        ("API", report.api_results),
    ):
        if not results:
            continue
        passed = sum(1 for item in results if item.passed)
        print(f"  {label}: {passed}/{len(results)} passed")
        for item in results:
            mark = "OK" if item.passed else "X"
            print(
                f"    {mark} {item.name} [{item.vector}] "
                f"provider={item.provider} cyber={item.cyber_score} fraud={item.fraud_score}"
            )
            for error in item.errors:
                print(f"        - {error}")

    if report.all_passed:
        print("\n  All escalation checks passed.")
        if report.fireworks_configured:
            print("  Live Fireworks cloud agent confirmed.")
        else:
            print("  Ran in MOCK mode — set FIREWORKS_API_KEY for live cloud verification.")
        return 0

    print("\n  One or more escalation checks failed.")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Test LangGraph cloud escalation for CYBER and FRAUD vectors.",
    )
    parser.add_argument(
        "--mode",
        choices=["graph", "api", "all"],
        default="all",
        help="Test mode: direct graph, live API, or both (default: all)",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"FastAPI base URL for API mode (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--require-fireworks",
        action="store_true",
        help="Fail if FIREWORKS_API_KEY is not set (reject mock client)",
    )
    parser.add_argument(
        "--enrichment-timeout",
        type=float,
        default=90.0,
        help="Seconds to wait for cloud SSE enrichment per scenario (default: 90)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Delay between API scenarios in seconds (default: 3)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        exit_code = asyncio.run(async_main(args))
    except KeyboardInterrupt:
        print("\nInterrupted.")
        exit_code = 130
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
