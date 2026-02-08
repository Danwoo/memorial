
import httpx
import asyncio
import json

BASE_URL = "http://127.0.0.1:8000"
OUTPUT_FILE = "api_test_result.txt"

def log(msg):
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

async def test_api():
    # Clear file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("Starting API Tests...\n")

    async with httpx.AsyncClient(timeout=10.0) as client:
        log("1. Health Check...")
        try:
            resp = await client.get(f"{BASE_URL}/health")
            log(f"   Status: {resp.status_code}")
            log(f"   Body: {resp.json()}")
        except Exception as e:
            log(f"   FAILED: {e}")
            return

        log("\n2. Create Memory (NOTE)...")
        try:
            payload = {
                "sourceType": "NOTE",
                "content": "This is a test memory from automated script."
            }
            resp = await client.post(f"{BASE_URL}/api/v1/memories", json=payload)
            log(f"   Status: {resp.status_code}")
            if resp.status_code == 201:
                log(f"   Created ID: {resp.json()['id']}")
            else:
                log(f"   Error: {resp.text}")
        except Exception as e:
            log(f"   FAILED: {e}")

        log("\n3. Create Chat Session...")
        session_id = None
        try:
            resp = await client.post(f"{BASE_URL}/api/v1/chat/sessions", json={"title": "Test Chat"})
            log(f"   Status: {resp.status_code}")
            if resp.status_code == 201:
                session_id = resp.json()['id']
                log(f"   Session ID: {session_id}")
            else:
                log(f"   Error: {resp.text}")
        except Exception as e:
            log(f"   FAILED: {e}")
            
        if session_id:
             log("\n4. Send Chat Message (Mock)...")
             try:
                payload = {"content": "Hello"}
                # Just confirm connection, not full SSE stream parsing
                async with client.stream("POST", f"{BASE_URL}/api/v1/chat/sessions/{session_id}/messages", json=payload) as response:
                     log(f"   Status: {response.status_code}")
             except Exception as e:
                log(f"   FAILED: {e}")
    
    log("\nAll tests completed.")

if __name__ == "__main__":
    asyncio.run(test_api())

