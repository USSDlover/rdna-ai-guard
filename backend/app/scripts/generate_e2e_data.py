#!/usr/bin/env python3
"""
RDNA AI Guard — End-to-End Demo Data Generator

Exercises the full ingestion pipeline so the Angular dashboard can be verified live:

  Health check → Fast seed (DB + SSE) → Full triage (Ollama + DB + SSE + LangGraph escalation)

Frontend surfaces to validate:
  - Cyber Grid (/dashboard/cyber-grid) — live telemetry matrix + virtual scroll
  - Ledger Audit (/dashboard/ledger-audit) — FRAUD / high-value filters + chart
  - Global threat toasts — events with risk_score > 85

Usage (from backend/):
  python -m app.scripts.generate_e2e_data
  python -m app.scripts.generate_e2e_data --seed 15 --watch-sse 30
  python -m app.scripts.generate_e2e_data --continuous --interval 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
API_PREFIX = "/api/v1"

# Long read timeout — first Ollama inference after cold start can take minutes.
TRIAGE_TIMEOUT = httpx.Timeout(connect=15.0, read=180.0, write=15.0, pool=15.0)
FAST_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)

TRIAGE_SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "Normal retail payment",
        "expect": "PASSED / low risk — baseline cyber-grid row",
        "payload": {
            "source_ip": "192.168.1.105",
            "request_path": "/api/v1/payments/initiate",
            "transaction_amount": 149.99,
            "account_token": "acct_****9034",
        },
    },
    {
        "name": "Routine balance inquiry",
        "expect": "PASSED — populates ledger with sub-threshold amounts",
        "payload": {
            "source_ip": "172.16.42.10",
            "request_path": "/api/v1/accounts/balance",
            "transaction_amount": 0.0,
            "account_token": "acct_****1178",
        },
    },
    {
        "name": "Cyber auth probe (ESCALATED)",
        "expect": "ESCALATED / CYBER — triggers LangGraph cloud escalation",
        "payload": {
            "source_ip": "45.33.12.88",
            "request_path": "/api/v1/auth/login",
            "transaction_amount": 0.0,
            "account_token": "acct_****4821",
        },
    },
    {
        "name": "High-value transfer (FRAUD)",
        "expect": "ESCALATED / FRAUD — ledger-audit chart + table",
        "payload": {
            "source_ip": "10.10.20.55",
            "request_path": "/api/v1/transfers",
            "transaction_amount": 14250.00,
            "account_token": "acct_****6620",
        },
    },
    {
        "name": "Critical ATO pattern (toast trigger)",
        "expect": "risk_score > 85 — global threat toast banner",
        "payload": {
            "source_ip": "185.220.101.42",
            "request_path": "/api/v1/auth/login",
            "transaction_amount": 18500.00,
            "account_token": "acct_****4821",
        },
    },
    {
        "name": "Syndicate routing spike",
        "expect": "ESCALATED — high velocity ledger signal",
        "payload": {
            "source_ip": "203.0.113.199",
            "request_path": "/api/v1/transfers",
            "transaction_amount": 24999.99,
            "account_token": "acct_****3391",
        },
    },
]


@dataclass
class RunStats:
    health_ok: bool = False
    seed_count: int = 0
    triage_ok: int = 0
    triage_failed: int = 0
    sse_events: int = 0
    escalated_seen: int = 0
    toast_candidates: int = 0


def _banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def _print_telemetry(label: str, telemetry: dict[str, Any], elapsed: float) -> None:
    risk = telemetry.get("risk_score", "?")
    status = telemetry.get("status", "?")
    vector = telemetry.get("primary_vector", "?")
    narrative = (telemetry.get("triage_narrative") or "")[:120]
    cloud = (telemetry.get("payload_metadata") or {}).get("cloud_escalation")

    print(f"  [{label}] {elapsed:.1f}s | risk={risk} status={status} vector={vector}")
    if narrative:
        print(f"           narrative: {narrative}...")
    if cloud:
        print(f"           cloud: cyber={cloud.get('cyber_score')} fraud={cloud.get('fraud_score')}")


async def check_health(client: httpx.AsyncClient, stats: RunStats) -> bool:
    _banner("STEP 1 — Backend health check")
    try:
        response = await client.get("/health", timeout=FAST_TIMEOUT)
        response.raise_for_status()
        body = response.json()
        print(f"  OK  {body.get('project')} — status {body.get('status')}")
        stats.health_ok = True
        return True
    except Exception as exc:
        print(f"  FAIL  Cannot reach backend: {exc}")
        print("  Hint: docker compose up --build   OR   uvicorn app.main:app --reload")
        return False


async def seed_baseline(
    client: httpx.AsyncClient,
    count: int,
    stats: RunStats,
) -> None:
    _banner(f"STEP 2 — Fast seed ({count} mock events → PostgreSQL + SSE)")
    try:
        response = await client.post(
            f"{API_PREFIX}/telemetry/seed",
            params={"count": count},
            timeout=FAST_TIMEOUT,
        )
        response.raise_for_status()
        body = response.json()
        stats.seed_count = int(body.get("seeded", 0))
        print(f"  OK  Seeded {stats.seed_count} events (no Ollama — instant baseline)")
    except Exception as exc:
        print(f"  WARN  Seed failed: {exc}")
        print("  Continuing with triage scenarios…")


async def run_triage_scenario(
    client: httpx.AsyncClient,
    scenario: dict[str, Any],
    index: int,
    stats: RunStats,
) -> None:
    name = scenario["name"]
    payload = scenario["payload"]
    print(f"\n  → Triage #{index}: {name}")
    print(f"     Expected: {scenario['expect']}")

    start = time.perf_counter()
    try:
        response = await client.post(
            f"{API_PREFIX}/telemetry/triage",
            json=payload,
            timeout=TRIAGE_TIMEOUT,
        )
        elapsed = time.perf_counter() - start

        if response.status_code != 200:
            stats.triage_failed += 1
            print(f"  FAIL  HTTP {response.status_code}: {response.text[:200]}")
            return

        body = response.json()
        telemetry = body.get("telemetry", {})
        stats.triage_ok += 1

        if telemetry.get("status") == "ESCALATED":
            stats.escalated_seen += 1
        if int(telemetry.get("risk_score", 0)) > 85:
            stats.toast_candidates += 1

        _print_telemetry("OK", telemetry, elapsed)

        if telemetry.get("status") == "ESCALATED":
            print("           ↳ LangGraph escalation scheduled — watch for enriched SSE update")

    except httpx.ReadTimeout:
        stats.triage_failed += 1
        print("  FAIL  Triage timed out (180s). Is Ollama running and model pulled?")
    except Exception as exc:
        stats.triage_failed += 1
        print(f"  FAIL  {exc}")


async def run_triage_batch(
    client: httpx.AsyncClient,
    stats: RunStats,
    delay: float,
) -> None:
    _banner(f"STEP 3 — Full triage pipeline ({len(TRIAGE_SCENARIOS)} Ollama scenarios)")
    print("  Each call: Ollama → PostgreSQL → SSE → optional LangGraph escalation\n")

    for index, scenario in enumerate(TRIAGE_SCENARIOS, start=1):
        await run_triage_scenario(client, scenario, index, stats)
        if index < len(TRIAGE_SCENARIOS):
            await asyncio.sleep(delay)


async def watch_sse(
    base_url: str,
    duration_seconds: float,
    stats: RunStats,
    stop_event: asyncio.Event,
) -> None:
    """Listen to the live SSE stream and print incoming telemetry summaries."""
    url = f"{base_url}{API_PREFIX}/telemetry/stream"
    deadline = time.perf_counter() + duration_seconds
    seen_ids: set[str] = set()

    print(f"\n  [SSE] Listening {duration_seconds:.0f}s on {url}")

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", url, timeout=None) as response:
                response.raise_for_status()
                event_name = ""
                async for raw_line in response.aiter_lines():
                    if stop_event.is_set() or time.perf_counter() > deadline:
                        break
                    if not raw_line:
                        continue
                    if raw_line.startswith("event:"):
                        event_name = raw_line.split(":", 1)[1].strip()
                        continue
                    if not raw_line.startswith("data:"):
                        continue
                    if event_name != "telemetry":
                        continue

                    try:
                        event = json.loads(raw_line.split(":", 1)[1].strip())
                    except json.JSONDecodeError:
                        continue

                    event_id = str(event.get("id", ""))
                    if event_id in seen_ids:
                        # Cloud escalation rebroadcasts the same id with enriched narrative
                        print(
                            f"  [SSE] UPDATE id={event_id[:8]}… "
                            f"risk={event.get('risk_score')} "
                            f"narrative={(event.get('triage_narrative') or '')[:60]}…"
                        )
                    else:
                        seen_ids.add(event_id)
                        stats.sse_events += 1
                        print(
                            f"  [SSE] NEW   id={event_id[:8]}… "
                            f"risk={event.get('risk_score')} "
                            f"status={event.get('status')} "
                            f"vector={event.get('primary_vector')}"
                        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        print(f"  [SSE] Stream ended: {exc}")


async def continuous_loop(
    client: httpx.AsyncClient,
    interval: float,
    stats: RunStats,
) -> None:
    _banner("CONTINUOUS MODE — Press Ctrl+C to stop")
    sequence = 0
    scenarios = TRIAGE_SCENARIOS

    while True:
        scenario = scenarios[sequence % len(scenarios)]
        await run_triage_scenario(client, scenario, sequence + 1, stats)
        sequence += 1
        await asyncio.sleep(interval)


async def async_main(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    stats = RunStats()

    _banner("RDNA AI Guard — E2E Demo Data Generator")
    print(f"  Target API : {base_url}")
    print(f"  Frontend   : http://localhost:4200/dashboard/cyber-grid")
    print(f"  Ledger     : http://localhost:4200/dashboard/ledger-audit")

    stop_sse = asyncio.Event()
    sse_task: asyncio.Task[None] | None = None

    async with httpx.AsyncClient(base_url=base_url) as client:
        if not await check_health(client, stats):
            return 1

        if args.watch_sse > 0:
            sse_task = asyncio.create_task(
                watch_sse(base_url, args.watch_sse, stats, stop_sse)
            )
            await asyncio.sleep(1.0)

        if not args.skip_seed and args.seed > 0:
            await seed_baseline(client, args.seed, stats)
            await asyncio.sleep(args.delay)

        if args.continuous:
            try:
                await continuous_loop(client, args.interval, stats)
            except KeyboardInterrupt:
                print("\n  Stopped continuous mode.")
        elif not args.skip_triage:
            await run_triage_batch(client, stats, args.delay)

        if args.continuous and not args.skip_triage:
            pass  # continuous already runs triage

        # Allow LangGraph background tasks to finish and rebroadcast
        if stats.escalated_seen > 0 and not args.continuous:
            wait = args.escalation_wait
            print(f"\n  Waiting {wait:.0f}s for cloud escalation rebroadcasts…")
            await asyncio.sleep(wait)

    stop_sse.set()
    if sse_task is not None:
        sse_task.cancel()
        try:
            await sse_task
        except asyncio.CancelledError:
            pass

    _banner("SUMMARY")
    print(f"  Health check        : {'OK' if stats.health_ok else 'FAIL'}")
    print(f"  Seed events         : {stats.seed_count}")
    print(f"  Triage success      : {stats.triage_ok}")
    print(f"  Triage failures     : {stats.triage_failed}")
    print(f"  Escalated events    : {stats.escalated_seen}")
    print(f"  Toast candidates    : {stats.toast_candidates} (risk > 85)")
    print(f"  SSE events observed : {stats.sse_events}")
    print()
    print("  Open the dashboard and confirm:")
    print("    • Cyber Grid table fills and virtual scrolls")
    print("    • Ledger Audit shows FRAUD / >$5k rows + velocity chart")
    print("    • Red toast banners appear for risk > 85")
    print("    • Escalated rows update with cloud synthesis narrative")
    print()

    return 0 if stats.triage_failed == 0 or stats.seed_count > 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate end-to-end demo telemetry for RDNA AI Guard.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"FastAPI base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=12,
        help="Number of fast mock events via POST /telemetry/seed (default: 12)",
    )
    parser.add_argument(
        "--skip-seed",
        action="store_true",
        help="Skip the fast seed phase",
    )
    parser.add_argument(
        "--skip-triage",
        action="store_true",
        help="Skip Ollama triage scenarios (seed only)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds between triage requests (default: 2.0)",
    )
    parser.add_argument(
        "--watch-sse",
        type=float,
        default=45.0,
        help="Seconds to listen on SSE stream in parallel (default: 45, 0=off)",
    )
    parser.add_argument(
        "--escalation-wait",
        type=float,
        default=15.0,
        help="Seconds to wait after triage for LangGraph rebroadcast (default: 15)",
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Loop triage scenarios until Ctrl+C",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=3.0,
        help="Seconds between requests in continuous mode (default: 3.0)",
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
