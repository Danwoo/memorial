# AWS EC2 배포 전 완전 검증 계획

**작성일**: 2026-03-08
**상태**: AWS EC2 운영 중 (memoir-api.duckdns.org)
**목표**: 안정적인 배포 + 서비스 무중단 전환

---

## 1. 현재 상황 분석

### 배포 구성도

```
┌─────────────────────────────────────────────────────────┐
│                     사용자 (브라우저)                      │
└────────────────┬────────────────────────────────────────┘
                 │ HTTPS
                 ▼
         ┌──────────────────┐
         │  Vercel (CDN)    │
         │   Front-end      │  ← main 브랜치 자동 배포
         │  memoir-*        │     (아직 미배포)
         └────────┬─────────┘
                  │ HTTP (CORS 허용)
                  │ CSP: AWS 백엔드 포함 ✓
                  ▼
        ┌─────────────────────────────┐
        │   AWS EC2 (memoir-api.duckdns.org)   │
        │   Backend (FastAPI)         │  ← 이미 운영 중
        │   + KuzuDB (로컬)           │     Docker 컨테이너
        │   :8000                     │     main 브랜치 자동 배포
        └────────────┬────────────────┘
                     │
                     ├── Supabase (PostgreSQL + pgvector)
                     │   otzqnucgfrlbqyyhksgo.supabase.co
                     │   ✓ 연결 확인
                     │
                     ├── Google Gemini (임베딩)
                     │   ✓ API 키 설정
                     │
                     ├── OpenAI (LLM)
                     │   ✓ API 키 설정
                     │
                     └── Kakao API (봇 연동)
                         ✓ API 키 설정
```

### 검증 상태

| 항목 | 상태 | 완료 | 비고 |
|------|------|------|------|
| AWS EC2 인스턴스 | ✓ 운영 중 | YES | memoir-api.duckdns.org |
| Docker 컨테이너 | ? 미확인 | 필수 | 헬스체크 필요 |
| Supabase 연결 | ? 미확인 | 필수 | 데이터 무결성 확인 |
| KuzuDB 상태 | ? 미확인 | 필수 | 그래프 노드 동기화 |
| CSP 업데이트 | ✓ 완료 | YES | 최신 커밋 포함 |
| Frontend 빌드 | ✓ 완료 | YES | npm run build 성공 |
| Backend 테스트 | ✓ 완료 | YES | pytest 통과 |
| 환경변수 보안 | ⚠ 부분 | 필수 | GitHub Secrets 이동 필요 |
| CORS 검증 | ? 미확인 | 필수 | preflight 테스트 |

---

## 2. 단계별 검증 계획 (총 40분)

### Phase 0: 보안 검증 [5분] ⭐ 최우선

> **목표**: 민감 정보 노출 방지

#### 0-1. .env 파일 보안
```bash
# ✓ 확인: .env는 .gitignore에 포함됨
git check-ignore backend/.env
# → no output = 성공 (파일이 ignored 상태)

# ✗ 문제 시
git rm --cached backend/.env  # 캐시 제거
```

#### 0-2. GitHub Secrets 설정 (필수 완료)
```bash
# GitHub Dashboard:
# https://github.com/Danwoo/memorial/settings/secrets/actions

# 필수 Secrets (AWS 배포용):
□ OPENAI_API_KEY=sk-proj-***
□ GOOGLE_API_KEY=AIza***
□ SUPABASE_SERVICE_ROLE_KEY=sb_secret_***
□ OPENROUTER_API_KEY=sk-or-v1-***
□ UPSTAGE_API_KEY=up_***
□ KAKAO_REST_API_KEY=7509***
```

#### 0-3. 환경변수 검증 체크리스트
```bash
# backend/.env 확인
grep "^[A-Z_]*=" backend/.env | wc -l
# → 15개 이상이어야 함

# 필수 변수 확인
required_vars=(
    "SUPABASE_URL"
    "SUPABASE_ANON_KEY"
    "SUPABASE_SERVICE_ROLE_KEY"
    "OPENAI_API_KEY"
    "GOOGLE_API_KEY"
    "ALLOWED_ORIGINS"
)

for var in "${required_vars[@]}"; do
    grep "^$var=" backend/.env || echo "✗ Missing: $var"
done
```

#### 0-4. CORS 설정 확인
```bash
# backend/.env의 ALLOWED_ORIGINS 확인
grep "^ALLOWED_ORIGINS=" backend/.env

# 예상 값:
# http://localhost:5173,http://localhost:3000,https://memoir-knowledge.vercel.app
```

**Phase 0 완료 조건**: 모든 ✓ 체크

---

### Phase 1: DB 연결 검증 [5분]

> **목표**: Supabase + KuzuDB 정상 운영 확인

#### 1-1. AWS EC2 헬스체크
```bash
# EC2 인스턴스 응답 확인
curl -v https://memoir-api.duckdns.org/health

# 예상 응답:
# HTTP/1.1 200 OK
# Content-Type: application/json
# {"status": "ok"}
```

**문제 해결**:
```bash
# EC2 접속
ssh -i ~/memoir-backend.pem ubuntu@memoir-api.duckdns.org

# Docker 상태 확인
docker ps | grep memoir-backend
# → RUNNING 상태여야 함

# 컨테이너 로그 확인
docker logs memoir-backend --tail 30

# 재시작 (필요 시)
docker restart memoir-backend
```

#### 1-2. Supabase 연결 검증
```bash
# 방법 1: 콘솔을 통한 직접 확인
# https://supabase.com/dashboard/project/otzqnucgfrlbqyyhksgo

# 방법 2: API를 통한 검증
python scripts/validate-db.py

# 예상 결과:
# ✓ Supabase 연결 성공
# ✓ KuzuDB 연결 성공
```

#### 1-3. 데이터 무결성 확인
```bash
# 상위 도메인 데이터 조회
# Supabase Dashboard > SQL Editor

-- 스크랩 테이블 확인
SELECT COUNT(*) as scrap_count FROM scraps;

-- 다이어리 테이블 확인
SELECT COUNT(*) as diary_count FROM diaries;

-- 사용자별 데이터 분포
SELECT user_id, COUNT(*) as item_count
FROM scraps
GROUP BY user_id
ORDER BY item_count DESC;
```

**데이터 손상 감지**:
- 스크랩이 갑자기 사라짐 → Render → AWS 마이그레이션 실패
  - **해결**: Supabase 백업에서 복구
- user_id 필터링 오류 → 다른 사용자 데이터 노출
  - **해결**: 백업에서 복구 + 코드 검증

#### 1-4. KuzuDB 상태 확인
```bash
# EC2에서 실행
docker exec memoir-backend python -c "
import kuzu
db = kuzu.database.Database('./kuzu_data')
conn = kuzu.connection.Connection(db)
result = conn.execute('MATCH (n) RETURN COUNT(n) AS count')
while result.has_next():
    print(result.get_next()['count'])
"

# 예상: 그래프 노드 수 (0 이상)
```

**Phase 1 완료 조건**:
- [ ] curl /health 200 OK
- [ ] Supabase 데이터 조회 성공
- [ ] KuzuDB 연결 성공

---

### Phase 2: CORS & CSP 검증 [5분]

> **목표**: Frontend ↔ Backend 통신 가능 확인

#### 2-1. CORS Preflight 검증
```bash
# OPTIONS 요청으로 CORS 헤더 확인
curl -i -X OPTIONS \
  -H "Origin: https://memoir-knowledge.vercel.app" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization" \
  https://memoir-api.duckdns.org/api/v1/scraps

# 예상 응답 헤더:
# Access-Control-Allow-Origin: https://memoir-knowledge.vercel.app
# Access-Control-Allow-Methods: GET,POST,PUT,DELETE,OPTIONS
# Access-Control-Allow-Headers: *
# Access-Control-Allow-Credentials: true
```

#### 2-2. CSP 헤더 검증
```bash
# Backend CSP 헤더 확인
curl -i https://memoir-api.duckdns.org/health | grep -i "content-security-policy"

# 예상: AWS 백엔드가 포함된 CSP
# (또는 CSP 미설정 = 기본값 사용)
```

#### 2-3. Vercel CSP 헤더 검증 (배포 후)
```bash
# vercel.json 확인
cat frontend/vercel.json | grep -A 10 "headers"

# 예상:
# "headers": [
#   {
#     "key": "Content-Security-Policy",
#     "value": "connect-src 'self' https://memoir-api.duckdns.org https://otzqnucgfrlbqyyhksgo.supabase.co ..."
#   }
# ]
```

**Phase 2 완료 조건**:
- [ ] OPTIONS 요청 200 응답
- [ ] CORS 헤더 포함
- [ ] Vercel CSP에 AWS 백엔드 포함

---

### Phase 3: API 엔드포인트 검증 [10분]

> **목표**: 주요 API가 정상 작동 확인

#### 3-1. 헬스체크
```bash
curl https://memoir-api.duckdns.org/health
# → {"status": "ok"}
```

#### 3-2. 인증 (Google OAuth)
```bash
# Google OAuth 콜백 URL 검증
# Frontend에서 Google 로그인 후 authorization code 수령

# Backend에서 토큰 교환
curl -X POST https://memoir-api.duckdns.org/api/v1/auth/google \
  -H "Content-Type: application/json" \
  -d '{
    "code": "<google_auth_code_from_frontend>",
    "redirect_uri": "http://localhost:5173/auth/callback"
  }'

# 예상 응답:
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIs...",
#   "user": {
#     "id": "user_xxx",
#     "email": "user@example.com"
#   }
# }
```

#### 3-3. 스크랩 조회 (데이터 접근)
```bash
# 토큰 저장
TOKEN="<access_token_from_above>"

# 스크랩 조회
curl -H "Authorization: Bearer $TOKEN" \
  https://memoir-api.duckdns.org/api/v1/scraps

# 예상 응답:
# {
#   "data": [
#     {
#       "id": "scrap_xxx",
#       "content": "...",
#       "created_at": "2026-03-08T..."
#     }
#   ],
#   "total": 42
# }
```

#### 3-4. 스크랩 생성
```bash
curl -X POST https://memoir-api.duckdns.org/api/v1/scraps \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Test scrap for validation",
    "source": "api-test"
  }'

# 예상: 201 Created + scrap 데이터
```

#### 3-5. Socrates 채팅 (LLM 통합)
```bash
# 1. 세션 생성
curl -X POST https://memoir-api.duckdns.org/api/v1/socrates/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Session"
  }'

# 2. 메시지 전송
SESSION_ID="<session_id_from_above>"

curl -X POST https://memoir-api.duckdns.org/api/v1/socrates/sessions/$SESSION_ID/messages \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "What do I think about resilience?"
  }'

# 예상: 200 OK + LLM 응답 스트리밍
```

**API 테스트 결과 기록**:
```
| Endpoint | Method | Status | Response Time | Notes |
|----------|--------|--------|----------------|-------|
| /health | GET | 200 | <100ms | ✓ |
| /auth/google | POST | 200 | <500ms | ✓ |
| /scraps | GET | 200 | <1s | ✓ |
| /scraps | POST | 201 | <2s | ✓ |
| /socrates/sessions | POST | 200 | <2s | ✓ |
| /socrates/.../messages | POST | 200 | <30s | ✓ (LLM 포함) |
```

**Phase 3 완료 조건**:
- [ ] 모든 API 응답 200/201
- [ ] 응답 시간 정상 범위
- [ ] 데이터 정합성 확인

---

### Phase 4: Frontend 통합 테스트 [15분]

> **목표**: 실제 사용자 시나리오 테스트

#### 4-1. 로컬 환경 설정
```bash
# Frontend API URL 설정
# frontend/src/config.ts (또는 환경변수)

const API_BASE_URL = 'https://memoir-api.duckdns.org';
// 또는 VITE_API_URL 환경변수

# 또는 .env.local
VITE_API_URL=https://memoir-api.duckdns.org
```

#### 4-2. 개발 서버 실행
```bash
cd frontend
npm run dev

# http://localhost:5173 에서 접속
```

#### 4-3. 사용자 시나리오 테스트 (수동)

**시나리오 1: 로그인**
- [ ] Google 로그인 클릭
- [ ] Google OAuth 팝업
- [ ] 리다이렉트 후 토큰 수신
- [ ] 대시보드 로드

**시나리오 2: 스크랩 생성**
- [ ] 스크랩 추가 버튼 클릭
- [ ] 텍스트 입력
- [ ] 저장 버튼
- [ ] 스크랩 목록에 추가됨 확인

**시나리오 3: 다이어리 작성**
- [ ] Diary 메뉴 선택
- [ ] 새 항목 작성
- [ ] AI 태그 생성 (비동기)
- [ ] 저장 확인

**시나리오 4: Socrates 대화**
- [ ] Socrates 메뉴 선택
- [ ] "What patterns do I see in my feedback?" 질문
- [ ] LLM 응답 스트리밍
- [ ] 응답 완료 대기

**시나리오 5: 캘린더 조회**
- [ ] Calendar 메뉴 선택
- [ ] 일자별 데이터 표시
- [ ] 스크랩/다이어리 개수 확인

#### 4-4. 브라우저 콘솔 확인
```javascript
// F12 > Console 탭

// 예상 메시지:
// - "API connected: https://memoir-api.duckdns.org"
// - 네트워크 요청 성공 (200, 201)

// 경고 (주의):
// ⚠ CORS 에러
// ⚠ 404 Not Found
// ⚠ 401 Unauthorized

// 오류 (반드시 해결):
// ✗ TypeError: Cannot read property
// ✗ Unhandled Promise Rejection
```

#### 4-5. 성능 확인 (DevTools)
```
F12 > Performance 탭

예상 수치:
- Page Load: < 3s
- API 응답: < 1s (일반), < 30s (LLM)
- 메모리 사용: < 100MB
- CPU: < 50%
```

**Phase 4 완료 조건**:
- [ ] 모든 시나리오 정상 작동
- [ ] 콘솔 에러 없음
- [ ] 응답 시간 정상 범위

---

### Phase 5: 보안 & 모니터링 검증 [5분]

> **목표**: 보안 위험 및 모니터링 설정 확인

#### 5-1. 입력 검증
```bash
# SQL Injection 시도
curl -X GET "https://memoir-api.duckdns.org/api/v1/scraps?search='; DROP TABLE scraps; --" \
  -H "Authorization: Bearer $TOKEN"

# 예상: 쿼리가 파라미터화되어 있어 안전함
# (에러 없음, 정상 응답 또는 empty result)

# XSS 시도
curl -X POST https://memoir-api.duckdns.org/api/v1/scraps \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "<script>alert(1)</script>"
  }'

# 예상: 스크립트가 HTML 이스케이프되어 저장됨
```

#### 5-2. 사용자 격리
```bash
# 다른 사용자 ID로 데이터 접근 시도
TOKEN_USER_A="<user_a_token>"
TOKEN_USER_B="<user_b_token>"

# User A의 스크랩 조회
curl -H "Authorization: Bearer $TOKEN_USER_A" \
  https://memoir-api.duckdns.org/api/v1/scraps | jq '.data[0].user_id'
# → "user_a_id"

# User B로 같은 엔드포인트 접근
curl -H "Authorization: Bearer $TOKEN_USER_B" \
  https://memoir-api.duckdns.org/api/v1/scraps | jq '.data[0].user_id'
# → "user_b_id" (User A 데이터 노출 안 됨)
```

#### 5-3. 로깅 확인
```bash
# EC2에서 Docker 로그 확인
docker logs memoir-backend --tail 100 | grep -E "ERROR|WARNING|user_id"

# 민감 정보가 로그에 기록되면 안 됨:
# ✗ API 키 (OPENAI_API_KEY, GOOGLE_API_KEY 등)
# ✗ JWT 토큰 (auth 헤더 전체)
# ✗ 비밀번호

# 정상 로그 예:
# 2026-03-08 12:34:56 - INFO - POST /api/v1/scraps - status=201
# 2026-03-08 12:34:57 - INFO - GET /api/v1/socrates/sessions/xxx - status=200
```

#### 5-4. 모니터링 대시보드 설정
```bash
# 1. AWS CloudWatch 설정
# https://console.aws.amazon.com/cloudwatch/

# 메트릭 확인:
# - EC2 CPU 사용률 (목표 < 50%)
# - EC2 메모리 (목표 < 70%)
# - 네트워크 트래픽

# 2. Vercel 로그
# https://vercel.com/dashboard/memoir-knowledge/logs

# 3. Render 로그 (기존 백엔드 비교)
# https://render.com/dashboard
# → memoir-backend-danwoo 서비스 > Logs
```

**Phase 5 완료 조건**:
- [ ] SQL Injection 안전
- [ ] XSS 방지 (HTML 이스케이프)
- [ ] 사용자 데이터 격리
- [ ] 로그에 민감 정보 없음

---

## 3. 검증 결과 기록 및 사인

검증을 완료한 후 아래를 작성하고 커밋합니다:

```markdown
# AWS 배포 검증 완료 보고서

**날짜**: 2026-03-08
**검증자**: [이름]
**상태**: ✅ 모든 검증 통과

## 검증 결과

### Phase 0: 보안 [✓]
- [x] .env 파일 gitignore 확인
- [x] GitHub Secrets 설정 (6개)
- [x] CORS 설정 확인

### Phase 1: DB 연결 [✓]
- [x] AWS EC2 /health 200 OK
- [x] Supabase 연결 성공
- [x] 데이터 무결성 확인
- [x] KuzuDB 그래프 노드 동기화

### Phase 2: CORS & CSP [✓]
- [x] CORS Preflight 헤더 정상
- [x] CSP 헤더에 AWS 백엔드 포함

### Phase 3: API 엔드포인트 [✓]
- [x] GET /health
- [x] POST /auth/google
- [x] GET /api/v1/scraps
- [x] POST /api/v1/scraps
- [x] POST /api/v1/socrates/sessions/...

### Phase 4: Frontend 통합 [✓]
- [x] 로그인 정상 작동
- [x] 스크랩 추가 정상 작동
- [x] 다이어리 작성 정상 작동
- [x] Socrates 대화 정상 작동
- [x] 콘솔 에러 없음

### Phase 5: 보안 & 모니터링 [✓]
- [x] SQL Injection 방지
- [x] XSS 방지
- [x] 사용자 데이터 격리 (user_id 필터)
- [x] 로그 정상

## 배포 승인

✅ **배포 권장**: 모든 검증 통과

**다음 단계**:
1. `git checkout main`
2. `git pull`
3. `git merge dev --no-ff`
4. `git push origin main`

배포 후 모니터링:
- CloudWatch 대시보드 활성화
- Vercel 로그 확인
- 사용자 피드백 수집
```

---

## 4. 문제 해결 가이드

### 문제: CORS 에러
```
Access-Control-Allow-Origin missing
```

**원인**: Backend CORS 미들웨어 미설정 또는 Vercel CSP 미설정

**해결**:
```python
# backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

```json
// frontend/vercel.json
{
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        {
          "key": "Access-Control-Allow-Origin",
          "value": "https://memoir-api.duckdns.org"
        }
      ]
    }
  ]
}
```

---

### 문제: 502 Bad Gateway (Vercel)

**원인**: Backend API 응답 시간 초과 (>30s)

**원인 분석**:
1. LLM 호출 지연
2. 벡터 검색 슬로우 쿼리
3. Supabase 데이터베이스 슬로우 쿼리

**해결**:
```bash
# 1. EC2에서 느린 쿼리 확인
docker logs memoir-backend --tail 50 | grep -E "SLOW|duration"

# 2. Supabase 슬로우 쿼리 로그
# https://supabase.com/dashboard > Logs

# 3. API 타임아웃 설정 확인
# backend/app/main.py
# SLOW_QUERY_TIMEOUT = 30  # 초

# 4. Vercel 함수 타임아웃
# vercel.json 또는 API route에 설정
```

---

### 문제: 401 Unauthorized

**원인**: JWT 토큰 만료 또는 잘못된 토큰

**해결**:
```javascript
// frontend/src/api/client.ts
// 토큰 갱신 로직
if (response.status === 401) {
    // 1. 토큰 갱신 시도
    const newToken = await refreshToken();
    // 2. 실패 시 로그인 화면으로 리다이렉트
    window.location.href = '/login';
}
```

---

### 문제: 데이터 손상 (Render → AWS 마이그레이션 실패)

**증상**: 스크랩/다이어리 데이터 누락

**해결**:
```bash
# 1. 마이그레이션 스크립트 검증
python backend/scripts/migrate_render_to_aws.py --dry-run

# 2. Supabase 백업에서 복구
# https://supabase.com/dashboard > Backup

# 3. 데이터 동기화
# 수동 마이그레이션 또는 재배포
```

---

## 5. 배포 롤백 계획

### 롤백 필요 조건

```
심각도 P1 (즉시 롤백)
- 데이터 손상 또는 유실
- 모든 사용자 로그인 불가
- 서비스 다운 (HTTP 5xx 계속 발생)

심각도 P2 (긴급 핫픽스)
- 특정 기능 오류 (예: Socrates 만 동작 안 함)
- 성능 저하 (응답 시간 10배 이상)
- 보안 취약점 (데이터 노출)
```

### 롤백 절차

#### 1. 긴급 중지 (1분)
```bash
# Vercel에서 배포 중단
# Render에서 이전 버전으로 재배포

# 또는 Frontend만 이전 버전으로 롤백
git revert <latest_commit_hash>
git push origin main
```

#### 2. 원인 분석 (5분)
```bash
# Vercel 빌드 로그
# https://vercel.com/dashboard/memoir-knowledge/deployments

# Render 런타임 로그
# https://render.com/dashboard > memoir-backend-danwoo

# AWS EC2 Docker 로그
ssh ubuntu@memoir-api.duckdns.org
docker logs memoir-backend --tail 100
```

#### 3. 데이터 복구 (필요 시)
```bash
# Supabase 백업 복구
# https://supabase.com/dashboard > Backups

# 또는 마지막 알려진 좋은 상태로 roll forward
git log --oneline | head -10  # 이전 커밋 찾기
```

#### 4. 재배포 (검증 후)
```bash
# 동일한 검증 프로세스 반복
bash scripts/pre-deploy-checklist.sh

# 통과 후 재배포
git push origin main
```

---

## 6. 체크리스트

### 배포 전
- [ ] AWS EC2 인스턴스 실행 중
- [ ] 모든 Phase 1-5 검증 통과
- [ ] GitHub Secrets 설정 완료
- [ ] Supabase 백업 생성
- [ ] Slack/이메일로 팀 공지

### 배포 중
- [ ] 커밋 이름: `Deploy: AWS EC2 완전 검증 완료`
- [ ] PR 설명: 검증 보고서 첨부
- [ ] CI 통과 대기 (GitHub Actions)
- [ ] Vercel Preview URL 테스트

### 배포 후
- [ ] 실제 프로덕션 환경에서 모든 기능 테스트 (2분)
- [ ] 로그 모니터링 (1시간)
- [ ] 성능 메트릭 확인 (CloudWatch)
- [ ] 사용자 피드백 모니터링

---

## 7. 참고: 자동화 스크립트

```bash
# 모든 검증 자동 실행
bash scripts/pre-deploy-checklist.sh

# API 엔드포인트 검증
bash scripts/validate-api.sh

# DB 연결 검증
python scripts/validate-db.py
```

---

**작성**: Claude Code
**마지막 업데이트**: 2026-03-08
**상태**: 활성

