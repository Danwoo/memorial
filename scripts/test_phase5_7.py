"""
Phase 5-7 Verification Test Script
Tests Backend API endpoints directly
"""
import sys
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test basic health endpoint"""
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"[HEALTH] Status: {r.status_code}")
        print(f"[HEALTH] Response: {r.json()}")
        return True
    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to backend server!")
        print("[ERROR] Make sure to run: cd backend && .venv\\Scripts\\python -m uvicorn app.main:app --port 8000")
        return False
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return False

def test_auth_endpoints():
    """Test auth endpoints exist"""
    print("\n--- AUTH ENDPOINTS ---")
    
    # Test login endpoint (should return validation error without proper data)
    try:
        r = requests.post(f"{BASE_URL}/api/v1/auth/login", json={}, timeout=5)
        print(f"[LOGIN] Status: {r.status_code} (422 = endpoint exists, validation error)")
    except Exception as e:
        print(f"[LOGIN] Error: {e}")
    
    # Test signup endpoint
    try:
        r = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={}, timeout=5)
        print(f"[SIGNUP] Status: {r.status_code} (422 = endpoint exists, validation error)")
    except Exception as e:
        print(f"[SIGNUP] Error: {e}")
    
    # Test me endpoint (should return 401 without token)
    try:
        r = requests.get(f"{BASE_URL}/api/v1/auth/me", timeout=5)
        print(f"[ME] Status: {r.status_code} (401 = endpoint exists, no auth)")
    except Exception as e:
        print(f"[ME] Error: {e}")

def test_search_endpoints():
    """Test search endpoints"""
    print("\n--- SEARCH ENDPOINTS ---")
    
    # Test search (should require query param)
    try:
        r = requests.get(f"{BASE_URL}/api/v1/search?q=test", timeout=5)
        print(f"[SEARCH] Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"[SEARCH] Response keys: {list(data.keys())}")
    except Exception as e:
        print(f"[SEARCH] Error: {e}")
    
    # Test related memories endpoint
    try:
        r = requests.get(f"{BASE_URL}/api/v1/search/related/test-id", timeout=5)
        print(f"[RELATED] Status: {r.status_code}")
    except Exception as e:
        print(f"[RELATED] Error: {e}")

def test_chat_endpoints():
    """Test chat endpoints"""
    print("\n--- CHAT ENDPOINTS ---")
    
    # Test create session
    try:
        r = requests.post(f"{BASE_URL}/api/v1/chat/sessions", json={}, timeout=5)
        print(f"[CREATE SESSION] Status: {r.status_code}")
        if r.status_code == 201:
            session = r.json()
            session_id = session.get("id")
            print(f"[CREATE SESSION] Session ID: {session_id}")
            
            # Test send message with mode
            if session_id:
                r2 = requests.post(
                    f"{BASE_URL}/api/v1/chat/sessions/{session_id}/messages",
                    json={"content": "테스트 메시지", "mode": "insight"},
                    timeout=30
                )
                print(f"[SEND MESSAGE] Status: {r2.status_code}")
    except Exception as e:
        print(f"[CHAT] Error: {e}")

def test_openapi_docs():
    """Test OpenAPI docs availability"""
    print("\n--- API DOCS ---")
    try:
        r = requests.get(f"{BASE_URL}/docs", timeout=5)
        print(f"[DOCS] Status: {r.status_code}")
        
        r2 = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
        if r2.status_code == 200:
            openapi = r2.json()
            paths = list(openapi.get("paths", {}).keys())
            print(f"[OPENAPI] Available paths ({len(paths)}): {paths[:10]}...")
    except Exception as e:
        print(f"[DOCS] Error: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("PHASE 5-7 VERIFICATION TEST")
    print("=" * 50)
    
    if not test_health():
        print("\n[FATAL] Backend server not running. Exiting.")
        sys.exit(1)
    
    test_auth_endpoints()
    test_search_endpoints()
    test_chat_endpoints()
    test_openapi_docs()
    
    print("\n" + "=" * 50)
    print("TEST COMPLETE")
    print("=" * 50)
