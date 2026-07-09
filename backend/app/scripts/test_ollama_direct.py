import json
import sys
import time
import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "gemma4:12b"

payload = {
    "model": MODEL_NAME,
    "messages": [
        {
            "role": "user",
            "content": (
                "Perform security triage on this log: IP=185.220.101.42, Path=/api/v1/auth/login, Amount=$12500. "
                "Return JSON with keys: risk_score (0-100), status ('PASSED' or 'ESCALATED'), "
                "primary_vector ('CYBER' or 'FRAUD'), and triage_narrative (short description)."
            ),
        }
    ],
    "format": "json",
    "stream": False,
    "keep_alive": "10m",
}


def run_test():
    print("=" * 75)
    print(f"🔍 [Diagnostic] Testing Direct Ollama Connection & Schema Mapping ({MODEL_NAME})")
    print("=" * 75)
    print(f"📡 Target URL: {OLLAMA_URL}")
    print("⏳ Waiting for raw Ollama API payload... This might take some time.\n")

    custom_timeout = httpx.Timeout(
        connect=10.0,
        read=180.0,
        write=10.0,
        pool=10.0
    )

    start_time = time.time()
    try:
        response = httpx.post(OLLAMA_URL, json=payload, timeout=custom_timeout)
        elapsed = time.time() - start_time

        if response.status_code == 200:
            raw_data = response.json()

            print(f"✅ SUCCESS ({elapsed:.2f}s)")
            print("=" * 75)
            print("📦 COMPLETE RAW OLLAMA RESPONSE SCHEMA:")
            print("=" * 75)
            print(json.dumps(raw_data, indent=2))
            print("=" * 75)

            # Diagnostic Extraction Test
            print("\n🔍 Field Extraction Checks:")
            message = raw_data.get("message", {})
            print(f"  • 'message' block exists : {bool(message)}")
            print(f"  • 'content' length       : {len(message.get('content', ''))}")
            print(f"  • 'thinking' block exists: {bool(message.get('thinking'))}")
            print(f"  • 'done_reason'          : '{raw_data.get('done_reason')}'")
            print(f"  • 'eval_count'           : {raw_data.get('eval_count')}")

        else:
            print(f"❌ FAILED with Status Code: {response.status_code}")
            print(response.text)

    except httpx.ConnectError:
        print("❌ CONNECTION ERROR: Ollama is not running on localhost:11434.")
    except httpx.ReadTimeout:
        print(f"⌛ TIMEOUT: Ollama took longer than 180 seconds to respond.")
    except Exception as e:
        print(f"❌ ERROR: {e}")


if __name__ == "__main__":
    run_test()