"""
Phase 8-9 Comprehensive Verification Script
Tests all new endpoints and validates code
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("PHASE 8-9 VERIFICATION TEST")
print("=" * 60)

# Test 1: Module imports
print("\n[1] Testing Module Imports...")
try:
    from app.core.config import get_settings
    print("   ✓ app.core.config")
    
    settings = get_settings()
    print(f"   ✓ Settings loaded - KAKAO_REST_API_KEY: {'SET' if settings.KAKAO_REST_API_KEY else 'NOT SET'}")
    
    from app.services import kakao
    print("   ✓ app.services.kakao")
    
    from app.api.v1.endpoints import integrations, stats
    print("   ✓ app.api.v1.endpoints.integrations")
    print("   ✓ app.api.v1.endpoints.stats")
    
    from app.api.v1.api import api_router
    print("   ✓ app.api.v1.api (api_router)")
    
except Exception as e:
    print(f"   ✗ Import Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Kakao service functions
print("\n[2] Testing Kakao Service...")
try:
    auth_url = kakao.get_auth_url("test_state")
    print(f"   ✓ get_auth_url(): {auth_url[:80]}...")
    
    # Test token storage
    kakao.set_stored_token("test_user", "test_token_123")
    retrieved = kakao.get_stored_token("test_user")
    assert retrieved == "test_token_123", "Token storage mismatch"
    print("   ✓ Token storage works")
    
except Exception as e:
    print(f"   ✗ Kakao Service Error: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Check router registration
print("\n[3] Testing Router Registration...")
try:
    routes = [r.path for r in api_router.routes]
    print(f"   Total routes: {len(routes)}")
    
    expected_routes = [
        "/integrations/kakao/auth",
        "/integrations/kakao/callback",
        "/integrations/kakao/send",
        "/integrations/kakao/status",
        "/stats/overview",
        "/stats/activity",
        "/stats/timeline"
    ]
    
    for expected in expected_routes:
        found = any(expected in r for r in routes)
        status = "✓" if found else "✗"
        print(f"   {status} {expected}")
        
except Exception as e:
    print(f"   ✗ Router Error: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Schema validation
print("\n[4] Testing Pydantic Schemas...")
try:
    from app.api.v1.endpoints.integrations import (
        KakaoAuthResponse, SendMessageRequest, SendMessageResponse
    )
    from app.api.v1.endpoints.stats import (
        OverviewStats, ActivityData, SourceStats, TagStats
    )
    
    # Test schema instantiation
    auth_resp = KakaoAuthResponse(auth_url="http://test", message="test")
    print("   ✓ KakaoAuthResponse")
    
    send_req = SendMessageRequest(title="Test", content="Test content")
    print("   ✓ SendMessageRequest")
    
    overview = OverviewStats(
        total_memories=100,
        total_this_week=10,
        total_this_month=30,
        most_active_day="2026-02-01"
    )
    print("   ✓ OverviewStats")
    
    activity = ActivityData(date="2026-02-01", count=5)
    print("   ✓ ActivityData")
    
except Exception as e:
    print(f"   ✗ Schema Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
