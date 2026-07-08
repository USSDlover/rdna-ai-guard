import asyncio
import random
import httpx

API_URL = "http://127.0.0.1:8000/api/v1/telemetry/triage"

# Mock datasets mimicking continuous web traffic & threat spikes
CLEAN_IPS = [
    "172.16.42.10", "192.168.1.105", "10.10.20.55",
    "203.0.113.12", "198.51.100.44"
]
MALICIOUS_IPS = [
    "45.33.12.88", "185.220.101.42", "10.0.0.77", "203.0.113.199"
]

PATHS = [
    "/api/v1/transfers", "/api/v1/auth/login",
    "/api/v1/payments/initiate", "/api/v1/accounts/balance"
]

ACCOUNT_TOKENS = [
    "acct_****4821", "acct_****9034", "acct_****1178", "acct_****6620"
]


def generate_payload(sequence: int) -> dict:
    """Generates a mix of normal traffic and anomalous threat spikes."""
    is_spike = sequence % 4 == 3

    if is_spike:
        is_cyber = sequence % 2 == 0
        return {
            "source_ip": random.choice(MALICIOUS_IPS) if is_cyber else random.choice(CLEAN_IPS),
            "request_path": "/api/v1/auth/login" if is_cyber else "/api/v1/transfers",
            "transaction_amount": 0.0 if is_cyber else round(random.uniform(8500.0, 24000.0), 2),
            "account_token": random.choice(ACCOUNT_TOKENS)
        }

    return {
        "source_ip": random.choice(CLEAN_IPS),
        "request_path": random.choice(PATHS),
        "transaction_amount": round(random.uniform(10.0, 4200.0), 2),
        "account_token": random.choice(ACCOUNT_TOKENS)
    }


async def run_simulation():
    print("🚀 Starting RDNA AI Guard Live Telemetry Traffic Simulation...")
    print("📡 Targets: FastAPI Server -> PostgreSQL Sync -> Live SSE Broadcaster -> Angular Dashboard\n")

    sequence = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        while True:
            payload = generate_payload(sequence)
            try:
                response = await client.post(API_URL, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    status = data["telemetry"]["status"]
                    score = data["telemetry"]["risk_score"]
                    print(
                        f"[{sequence:04d}] Sent payload from {payload['source_ip']} | Risk: {score} | Status: {status}")
                else:
                    print(f"❌ Server Error: {response.status_code}")
            except Exception as e:
                print(f"⚠️ Connection Failed: {e}. Is your FastAPI backend running on port 8000?")

            sequence += 1
            # Simulate natural bursty network traffic (0.5s to 2.5s delay)
            await asyncio.sleep(random.uniform(0.5, 2.5))


if __name__ == "__main__":
    asyncio.run(run_simulation())
