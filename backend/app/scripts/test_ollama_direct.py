import sys
import time
import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "gemma4:12b"  # or gemma4:31b

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
    # Keeps the model pre-loaded in memory for 10 minutes to avoid repeated cold-start delays
    "keep_alive": "10m",
}


def run_test():
    print("=" * 65)
    print(f"🔍 [1/2] Testing Direct Ollama Connection ({MODEL_NAME})")
    print("=" * 65)
    print(f"📡 Target URL: {OLLAMA_URL}")
    print("⏳ Waiting for Gemma 4 to load into memory & generate response...\n")

    # Grant up to 180s for model loading + inference thinking
    custom_timeout = httpx.Timeout(
        connect=10.0,   # Max time to open connection to Ollama
        read=180.0,     # Max time to wait for model to return complete JSON
        write=10.0,
        pool=10.0
    )

    start_time = time.time()
    try:
        response = httpx.post(OLLAMA_URL, json=payload, timeout=custom_timeout)
        elapsed = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            content = data.get("message", {}).get("content", "{}")

            print(f"✅ SUCCESS ({elapsed:.2f}s)")
            print("-" * 65)
            print("🤖 Raw Gemma Response:")
            print(content)
            print("-" * 65)
        else:
            print(f"❌ FAILED with Status Code: {response.status_code}")
            print(response.text)

    except httpx.ConnectError:
        print("❌ CONNECTION ERROR: Ollama is not running on localhost:11434.")
    except httpx.ReadTimeout:
        print(f"⌛ TIMEOUT: Ollama took longer than 180 seconds to respond. Check Docker GPU/RAM allocations.")
    except Exception as e:
        print(f"❌ ERROR: {e}")


if __name__ == "__main__":
    run_test()