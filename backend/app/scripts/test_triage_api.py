import sys
import time
import httpx

FASTAPI_URL = "http://localhost:8000/api/v1/telemetry/triage"

# Test payloads: 1 Normal, 1 Cyber Spike
test_cases = [
    {
        "name": "Normal User Request",
        "data": {
            "source_ip": "192.168.1.105",
            "request_path": "/api/v1/payments/initiate",
            "transaction_amount": 150.00,
            "account_token": "acct_****9034",
        },
    },
    {
        "name": "High-Risk Suspicious Attack",
        "data": {
            "source_ip": "185.220.101.42",
            "request_path": "/api/v1/auth/login",
            "transaction_amount": 18500.00,
            "account_token": "acct_****4821",
        },
    },
]


def run_test():
    print("=" * 65)
    print("🚀 [2/2] Testing FastAPI Telemetry Triage Endpoint")
    print("=" * 65)
    print(f"📡 Target Endpoint: {FASTAPI_URL}\n")

    # Grant up to 180s timeout to allow local LLM thinking & VRAM loading
    custom_timeout = httpx.Timeout(
        connect=10.0,
        read=180.0,
        write=10.0,
        pool=10.0,
    )

    for idx, test in enumerate(test_cases, 1):
        print(f"----- Test Case #{idx}: {test['name']} -----")
        print("⏳ Waiting for backend triage pipeline...")
        start_time = time.time()
        try:
            res = httpx.post(FASTAPI_URL, json=test["data"], timeout=custom_timeout)
            elapsed = time.time() - start_time

            if res.status_code == 200:
                body = res.json()
                telemetry = body.get("telemetry", {})

                print(f"✅ Status: {res.status_code} ({elapsed:.2f}s)")
                print(f"   • Risk Score    : {telemetry.get('risk_score')}")
                print(f"   • Triage Status : {telemetry.get('status')}")
                print(f"   • Vector        : {telemetry.get('primary_vector')}")
                print(f"   • Narrative     : {telemetry.get('triage_narrative')}")
            else:
                print(f"❌ FAILED ({res.status_code}): {res.text}")

        except httpx.ConnectError:
            print("❌ CONNECTION ERROR: FastAPI is not running on localhost:8000.")
            break
        except httpx.ReadTimeout:
            print("⌛ TIMEOUT: Request exceeded 180s threshold while waiting for local Ollama.")
        except Exception as e:
            print(f"❌ ERROR: {e}")
        print()


if __name__ == "__main__":
    run_test()