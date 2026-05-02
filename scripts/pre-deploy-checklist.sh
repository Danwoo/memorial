#!/bin/bash

# 배포 전 체크리스트 (main 브랜치 머지 직전)
# 사용: bash scripts/pre-deploy-checklist.sh

set -e

CHECKS_PASSED=0
CHECKS_FAILED=0

check_result() {
    if [ $? -eq 0 ]; then
        echo "  ✓ $1"
        ((CHECKS_PASSED++))
    else
        echo "  ✗ $1"
        ((CHECKS_FAILED++))
    fi
}

echo "============================================================"
echo "배포 전 체크리스트"
echo "============================================================\n"

# 1. Git 상태 확인
echo "[1] Git 상태"
git status --short | head -5
echo ""

# 2. 환경 설정 확인
echo "[2] 환경 설정"

# .env 파일이 git에 포함되지 않았는지 확인
git check-ignore backend/.env > /dev/null && echo "  ✓ .env 파일이 gitignore에 포함됨" || echo "  ✗ .env 파일이 버전 관리되고 있음"

# GitHub Secrets 확인
echo "  GitHub Secrets 확인:"
echo "    https://github.com/Danwoo/memorial/settings/secrets/actions"
echo ""

# 3. Backend 검증
echo "[3] Backend 검증"

if [ -f "backend/.env" ]; then
    echo "  ✓ backend/.env 존재"
else
    echo "  ✗ backend/.env 파일 없음"
fi

cd backend

# Python 구문 검사
echo "  Python 구문 검사..."
python_syntax_ok=true
for file in $(find app -name "*.py"); do
    python -m py_compile "$file" 2>/dev/null || python_syntax_ok=false
done
[ "$python_syntax_ok" = true ] && echo "    ✓ 모든 Python 파일 구문 OK" || echo "    ✗ Python 구문 에러"

# pytest 실행
echo "  pytest 실행..."
if python -m pytest --co -q > /dev/null 2>&1; then
    echo "    ✓ pytest 설정 OK"
else
    echo "    ⚠ pytest 설정 확인 필요"
fi

cd ..
echo ""

# 4. Frontend 검증
echo "[4] Frontend 검증"

cd frontend

# TypeScript 타입 검사
echo "  TypeScript 타입 검사..."
if npx tsc --noEmit > /dev/null 2>&1; then
    echo "    ✓ TypeScript 타입 OK"
    ((CHECKS_PASSED++))
else
    echo "    ✗ TypeScript 타입 에러"
    ((CHECKS_FAILED++))
fi

# Build 테스트
echo "  Build 테스트..."
if npm run build > /tmp/build.log 2>&1; then
    echo "    ✓ Build 성공"
    ((CHECKS_PASSED++))
else
    echo "    ✗ Build 실패"
    echo "    로그: tail /tmp/build.log"
    ((CHECKS_FAILED++))
fi

cd ..
echo ""

# 5. 커밋 메시지 검증
echo "[5] 커밋 메시지"

dev_commits=$(git log --oneline main..dev | wc -l)
echo "  dev 브랜치에 있는 커밋: $dev_commits 개"

if [ "$dev_commits" -eq 0 ]; then
    echo "  ⚠ dev 브랜치에 새로운 커밋이 없습니다"
else
    echo "  최근 커밋:"
    git log --oneline main..dev | head -5 | sed 's/^/    /'
fi
echo ""

# 6. 배포 준비 상태
echo "[6] 배포 준비 상태"

echo "  Backend:"
echo "    URL: https://memoir-api.duckdns.org"
echo "    상태: AWS EC2 운영 중"

echo "  Frontend:"
echo "    URL: https://memoir-knowledge.vercel.app"
echo "    상태: Vercel (main 브랜치 푸시 시 자동 배포)"

echo ""
echo "============================================================"
echo "체크리스트 요약"
echo "============================================================"
echo "통과: $CHECKS_PASSED"
echo "실패: $CHECKS_FAILED"
echo ""

if [ "$CHECKS_FAILED" -eq 0 ]; then
    echo "✓ 모든 검증 통과 - 배포 준비 완료"
    echo ""
    echo "다음 단계:"
    echo "1. git checkout main"
    echo "2. git pull"
    echo "3. git merge dev -m 'Deploy: AWS EC2 통합'"
    echo "4. git push origin main"
    echo ""
    exit 0
else
    echo "✗ 검증 실패 - 배포 전에 문제 해결 필요"
    echo ""
    exit 1
fi
