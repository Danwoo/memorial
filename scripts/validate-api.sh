#!/bin/bash

# AWS EC2 API 검증 스크립트
# Phase 1: DB 연결
# Phase 2: CORS & CSP
# Phase 3: API 기본 기능

set -e

API_URL="${1:-https://memoir-api.duckdns.org}"
VERCEL_URL="https://memoir-knowledge.vercel.app"

echo "============================================================"
echo "AWS EC2 API 검증 시작"
echo "API URL: $API_URL"
echo "============================================================"

# Phase 1: 헬스체크
echo -e "\n[Phase 1] 헬스체크..."
if curl -s -f "$API_URL/health" > /dev/null; then
    echo "✓ API 응답: OK"
else
    echo "✗ API 응답: FAILED (응답 없음)"
    echo "  → EC2 인스턴스 상태 확인: https://memoir-api.duckdns.org"
    exit 1
fi

# Phase 2: CORS 검증
echo -e "\n[Phase 2] CORS preflight 검증..."
cors_response=$(curl -s -i -X OPTIONS \
    -H "Origin: $VERCEL_URL" \
    -H "Access-Control-Request-Method: GET" \
    "$API_URL/api/v1/scraps" 2>&1)

if echo "$cors_response" | grep -q "Access-Control-Allow-Origin"; then
    echo "✓ CORS 헤더: 설정됨"
    echo "$cors_response" | grep "Access-Control-Allow"
else
    echo "⚠ CORS 헤더: 미설정 또는 제한"
    echo "  → backend/app/main.py에서 CORS 미들웨어 확인 필요"
fi

# Phase 3: DB 연결 상태 체크
echo -e "\n[Phase 3] DB 연결 상태..."
echo "  (실시간 모니터링은 아래 명령어 사용)"
echo "  - EC2 접속: ssh ubuntu@memoir-api.duckdns.org"
echo "  - Docker 상태: docker ps"
echo "  - 로그 확인: docker logs memoir-backend --tail 20"

# Phase 4: API 엔드포인트 목록
echo -e "\n[Phase 4] 주요 엔드포인트..."
echo "  GET   $API_URL/health                          [헬스체크]"
echo "  POST  $API_URL/api/v1/auth/google              [로그인]"
echo "  GET   $API_URL/api/v1/scraps                   [스크랩 조회]"
echo "  POST  $API_URL/api/v1/scraps                   [스크랩 생성]"
echo "  POST  $API_URL/api/v1/socrates/sessions        [Socrates 세션]"

echo -e "\n============================================================"
echo "API 검증 완료"
echo "다음 단계: Phase 4 (Frontend 통합 테스트)로 진행"
echo "============================================================\n"
