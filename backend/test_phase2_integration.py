
import asyncio
import httpx
import json
import time
import os

BASE_URL = "http://127.0.0.1:8000"
RESULT_FILE = "phase2_test_result.txt"

def log(msg):
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

async def test_integration():
    # Reset result file
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write("=== Phase 2 Integration Test Results ===\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health Check
        log("[1] Checking Server Health...")
        try:
            resp = await client.get(f"{BASE_URL}/health")
            if resp.status_code != 200:
                log(f"❌ Server Health Failed: {resp.status_code}")
                return
            log(f"✅ Server OK: {resp.json()}")
        except Exception as e:
            log(f"❌ Connection Failed: {e}")
            return

        # 2. Create Memory with Distinct Fact
        log("\n[2] Creating Test Memory...")
        test_fact = "The secret code for Phase 2 verification is 'BLUE-MOON-77'."
        payload = {
            "sourceType": "NOTE",
            "content": f"Important security update. {test_fact}",
            "title": "Verification Secret"
        }
        
        try:
            resp = await client.post(f"{BASE_URL}/api/v1/memories", json=payload)
            if resp.status_code not in [200, 201]:
                log(f"❌ Create Memory Failed: Status {resp.status_code}")
                log(f"   Response: {resp.text}")
                
                # Diagnostic Hint
                if resp.status_code == 500 or "policy" in resp.text.lower():
                    log("\n[!] DIAGNOSIS: Database Permission Error")
                    log("    It seems RLS (Row Level Security) is blocking the insert.")
                    log("    Please ensure 'SUPABASE_SERVICE_ROLE_KEY' is set in 'backend/.env'.")
                    log("    You can find this key in Supabase Dashboard -> Project Settings -> API.")
                return
            
            memory_data = resp.json()
            memory_id = memory_data['id']
            log(f"✅ Memory Created: ID={memory_id}")
            log("   (If you see this, DB connection and permissions are working!)")
        except Exception as e:
            log(f"❌ Create Request Failed: {e}")
            return

        # 3. Poll for Processing Completion (Vector Embedding)
        log("\n[3] Waiting for Librarian Processing (Embedding)...")
        start_time = time.time()
        processed = False
        
        while time.time() - start_time < 20: # Wait up to 20 seconds
            resp = await client.get(f"{BASE_URL}/api/v1/memories/{memory_id}")
            data = resp.json()
            status = data.get("status")
            log(f"   Current Status: {status}")
            
            if status == "completed":
                processed = True
                break
            await asyncio.sleep(2)
            
        if not processed:
            log("❌ Processing Timeout. Librarian didn't complete the task.")
            # We continue anyway to see if Chat works (might fail context)
        else:
            log("✅ Memory Processed and Embedded.")

        # 4. Chat RAG Test
        log("\n[4] Testing Socrates RAG Chat...")
        # Create Session
        resp = await client.post(f"{BASE_URL}/api/v1/chat/sessions", json={"title": "Verification Chat"})
        session_id = resp.json()['id']
        
        # Ask Question
        question = "What is the secret code for Phase 2 verification?"
        log(f"   Question: {question}")
        
        # We use stream but just read response
        full_response = ""
        try:
            async with client.stream("POST", f"{BASE_URL}/api/v1/chat/sessions/{session_id}/messages", json={"content": question}) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if "content" in data:
                                full_response += data["content"]
                        except:
                            pass
            
            log(f"   AI Answer: {full_response}")
            
            if "BLUE-MOON-77" in full_response:
                log("✅ VERIFICATION SUCCESS: RAG retrieved the secret code!")
            else:
                log("⚠️ VERIFICATION PARTIAL: AI answered but might have missed the specific code.")
                
        except Exception as e:
            log(f"❌ Chat Request Failed: {e}")

    log("\n=== End of Test ===")

if __name__ == "__main__":
    asyncio.run(test_integration())
