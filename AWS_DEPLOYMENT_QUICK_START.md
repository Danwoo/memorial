# AWS EC2 배포 전 검증 - 빠른 시작 가이드

**총 소요 시간**: 40분
**복잡도**: 중간
**위험도**: 낮음 (기존 서비스 무중단)

---

## 🎯 5분 요약

현재 상황:
- AWS EC2에서 backend가 **이미 운영 중** (memoir-api.duckdns.org)
- Frontend는 **Vercel에 배포할 준비** (main 브랜치 미병합)
- **CSP 업데이트는 완료** (AWS 백엔드 포함)

목표:
- **안정적인 배포** 보장
- **데이터 손상 방지**
- **보안 검증** 완료

---

## 📋 필수 체크리스트 (5분)

다음을 **지금 바로** 확인하세요:

```bash
# 1. GitHub Secrets 확인
# https://github.com/Danwoo/memorial/settings/secrets/actions
# 필수: OPENAI_API_KEY, GOOGLE_API_KEY, SUPABASE_SERVICE_ROLE_KEY 등

# 2. .env 보안 확인
git check-ignore backend/.env
# → (출력 없음) = 정상 (파일이 무시됨)

# 3. 빌드 테스트
cd frontend && npm run build
cd ../backend && python -m pytest --co -q

# 4. 커밋 메시지 확인
git log --oneline main..dev | head -5
```

---

## 🚀 단계별 실행 (30분)

### Step 1: Phase 0 보안 검증 (5분)

```bash
# 1. 환경변수 확인
cd backend
grep "^SUPABASE_URL=" .env
grep "^ALLOWED_ORIGINS=" .env

# 2. .env 파일이 git에서 제외되었는지 확인
cd ..
git status | grep "\.env"
# → 아무것도 나타나지 않아야 함 (정상)

# 결과 기록
# ✓ .env 보안 OK
# ✓ GitHub Secrets 설정 확인
```

### Step 2: Phase 1 DB 연결 검증 (5분)

```bash
# 1. AWS EC2 헬스체크
curl -v https://memoir-api.duckdns.org/health

# 예상 응답:
# HTTP/1.1 200 OK
# {"status": "ok"}

# 2. Python 검증 스크립트 실행
cd backend
python ../scripts/validate-db.py

# 결과 기록
# ✓ Supabase 연결 OK
# ✓ KuzuDB 상태 확인
```

### Step 3: Phase 2 CORS 검증 (3분)

```bash
# CORS preflight 테스트
curl -i -X OPTIONS \
  -H "Origin: https://memoir-knowledge.vercel.app" \
  -H "Access-Control-Request-Method: GET" \
  https://memoir-api.duckdns.org/api/v1/scraps

# 출력에 다음이 포함되어야 함:
# Access-Control-Allow-Origin: https://memoir-knowledge.vercel.app

# 결과 기록
# ✓ CORS 헤더 정상
```

### Step 4: Phase 3 API 검증 (10분)

```bash
# API 검증 스크립트 실행
bash scripts/validate-api.sh https://memoir-api.duckdns.org

# 또는 Postman/REST Client 사용:
# 1. GET https://memoir-api.duckdns.org/health → 200 OK
# 2. POST /api/v1/auth/google → 200 (또는 요청 형식 에러)
# 3. GET /api/v1/scraps → 401 (토큰 필요) 또는 200 (데이터)

# 결과 기록
# ✓ 모든 엔드포인트 응답 정상
```

### Step 5: Phase 4 Frontend 통합 (10분)

```bash
# 1. API URL 설정
cat frontend/src/config.ts | grep -i "api"
# → 또는 VITE_API_URL 환경변수 설정

# 2. 로컬 개발 서버 실행
cd frontend
npm run dev
# → http://localhost:5173

# 3. 브라우저에서 테스트:
# - Google 로그인 클릭
# - 스크랩 추가 클릭
# - Socrates 대화 테스트
# - 콘솔 에러 확인 (F12 > Console)

# 결과 기록
# ✓ Frontend-Backend 통신 정상
# ✓ 콘솔 에러 없음
```

### Step 6: 배포 승인 및 실행 (5분)

```bash
# 모든 검증 통과 확인
bash scripts/pre-deploy-checklist.sh

# main 브랜치 머지 및 배포
git checkout main
git pull
git checkout dev
git log --oneline main..dev | head -1

# 최종 커밋 메시지
git checkout main
git merge dev --no-ff -m "Deploy: AWS EC2 완전 검증 완료 (P0-1~P0-5)"
git push origin main

# 예상 결과:
# 1. GitHub Actions CI 통과
# 2. Vercel 자동 배포
# 3. Backend (Render 기존 또는 AWS 신규)
```

---

## ⚠️ 문제 해결 (즉시 참고)

### CORS 에러
```
ERROR: No 'Access-Control-Allow-Origin' header
```
→ backend/app/main.py의 CORS 미들웨어 확인
→ `ALLOWED_ORIGINS` 환경변수에 Vercel 도메인 포함 필요

### API 응답 없음 (curl timeout)
```bash
ssh ubuntu@memoir-api.duckdns.org
docker ps
docker logs memoir-backend --tail 20
docker restart memoir-backend
```

### 데이터 조회 불가 (401 Unauthorized)
```bash
# JWT 토큰 필요
# Frontend에서 Google 로그인 후 Authorization 헤더에 토큰 추가

curl -H "Authorization: Bearer <token>" \
  https://memoir-api.duckdns.org/api/v1/scraps
```

### 502 Bad Gateway (Vercel)
```
원인: LLM 호출 30초 초과
→ API 응답 시간 줄이기
→ Vercel 함수 타임아웃 설정 확인
```

---

## 📊 검증 결과 기록

검증 완료 후 다음을 복사하여 커밋 메시지에 추가:

```markdown
## AWS EC2 배포 검증 완료

### ✓ Phase 0: 보안
- GitHub Secrets 6개 설정
- .env 파일 gitignore 확인
- CORS 설정 완료

### ✓ Phase 1: DB 연결
- Supabase 연결 성공
- KuzuDB 동기화 확인

### ✓ Phase 2: CORS & CSP
- CORS preflight 정상
- CSP 헤더 포함

### ✓ Phase 3: API 엔드포인트
- GET /health: 200
- POST /auth/google: OK
- GET /api/v1/scraps: OK

### ✓ Phase 4: Frontend 통합
- 로그인 정상 작동
- 데이터 조회 정상 작동
- 콘솔 에러 없음

### ✓ Phase 5: 보안 & 모니터링
- SQL Injection 방지 확인
- 사용자 데이터 격리 확인

**배포 승인**: ✅ 모든 항목 통과
```

---

## 🔗 상세 가이드

더 자세한 정보는 다음을 참고하세요:

📄 **AWS_DEPLOYMENT_VALIDATION.md** (전체 검증 계획)
- 5개 Phase 상세 설명
- curl 명령어 예시
- 문제 해결 가이드
- 롤백 계획

📄 **scripts/validate-api.sh** (API 자동 검증)
```bash
bash scripts/validate-api.sh https://memoir-api.duckdns.org
```

📄 **scripts/validate-db.py** (DB 연결 검증)
```bash
python scripts/validate-db.py
```

📄 **scripts/pre-deploy-checklist.sh** (배포 전 체크리스트)
```bash
bash scripts/pre-deploy-checklist.sh
```

---

## 🎯 핵심 포인트

✅ **이미 완료된 것**:
- AWS EC2 인스턴스 운영
- CSP 헤더 업데이트
- Frontend 빌드 성공
- Backend pytest 통과

⏳ **지금 해야 할 것**:
1. Phase 0-5 검증 실행 (30분)
2. 모든 체크박스 완료 확인
3. main 브랜치 머지 (5분)
4. Vercel/AWS 배포 모니터링 (10분)

⚠️ **주의사항**:
- Supabase 백업 확인 후 진행
- 배포 후 1시간 모니터링 필수
- 문제 발생 시 즉시 롤백 준비

---

## 💬 예상 질문

**Q: AWS EC2에서 이미 운영 중인데, 왜 검증이 필요한가?**
A: Frontend 배포 시 API 연결을 최종 확인하고, 데이터 손상/보안 이슈를 사전에 방지하기 위함

**Q: 검증 중 문제 발생 시?**
A: AWS_DEPLOYMENT_VALIDATION.md의 문제 해결 섹션 참고, 또는 기존 Render 백엔드로 임시 롤백

**Q: Phase별 소요 시간?**
A: 각 Phase 3-15분, 총 40분 (문제 없을 경우)

**Q: 언제 배포하면 되나?**
A: 모든 Phase 1-5 ✓ 완료 후 main 브랜치 머지

---

**최종 확인**: 모든 체크박스 ✓ 완료 후 배포 진행!

시간: `2026-03-08 작성`
상태: `검증 준비 완료`

