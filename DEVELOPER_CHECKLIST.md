# ✅ Memoir 버그 해결 개발자 체크리스트

**Issue #6 & #7 해결을 위한 단계별 가이드**

---

## 🔴 Issue #6: 다이어리 좌측 화살표 네비게이션 (Digest API Hanging)

### 단계 1: 문제 재현 ✓ (DONE)
- [x] 브라우저에서 /diary 페이지 접속
- [x] 좌측 화살표 클릭
- [x] 검은 화면 확인
- [x] DevTools Network 탭에서 `/digest/date/{date}` 요청이 PENDING 상태 확인

### 단계 2: 백엔드 로그 확인
- [ ] EC2 서버 접속
  ```bash
  ssh -i <키_파일> ubuntu@15.165.17.222
  ```
- [ ] Docker 로그 확인
  ```bash
  cd /home/ubuntu/memorial
  docker logs memoir-backend | tail -500 > backend_logs.txt
  ```
- [ ] 에러 메시지 검색
  ```bash
  docker logs memoir-backend | grep -i "digest\|error\|exception\|timeout"
  ```

### 단계 3: 코드 검사
- [ ] 파일 위치 확인: `backend/app/routers/` 에서 digest 관련 라우터 찾기
  ```bash
  find backend -name "*digest*" -type f
  ```
- [ ] 라우터 코드 검토
  - [ ] 함수 이름: `get_digest()` 또는 유사
  - [ ] 쿼리 성능 확인
  - [ ] 에러 처리 확인
  - [ ] 타임아웃 설정 확인

### 단계 4: 데이터베이스 쿼리 검사
- [ ] Supabase 콘솔 접속 (https://supabase.com)
- [ ] 해당 쿼리 실행 시간 측정
  ```sql
  -- 예상 쿼리 (실제 쿼리 확인 후 수정)
  SELECT * FROM digests
  WHERE user_id = 'c056c1c5-93ce-4a2b-84b9-3d622d185093'
  AND date = '2026-03-16';
  ```
- [ ] 실행 시간이 정상 범위인지 확인 (< 1초)

### 단계 5: 로컬 테스트
- [ ] 로컬 백엔드 실행
  ```bash
  cd backend
  python -m uvicorn app.main:app --reload
  ```
- [ ] API 직접 호출
  ```bash
  curl -s http://localhost:8000/api/v1/digest/date/2026-03-16 \
    -H "Authorization: Bearer <테스트_토큰>"
  ```
- [ ] 응답 시간 및 상태 확인

### 단계 6: 해결 및 배포
- [ ] 원인 파악 후 코드 수정
- [ ] 로컬 테스트 통과 확인
- [ ] 커밋 및 푸시
  ```bash
  git add backend/app/...
  git commit -m "fix: digest API timeout/error issue"
  git push origin dev
  ```
- [ ] EC2 서버 배포
  ```bash
  ssh ubuntu@15.165.17.222
  cd /home/ubuntu/memorial
  git pull origin dev
  docker compose up -d --build
  ```
- [ ] 재테스트
  - [ ] 브라우저에서 /diary 접속
  - [ ] 좌측 화살표 클릭
  - [ ] March 16 다이어리 로드 확인 (검은 화면 아님)

---

## 🔴 Issue #7: 스크랩 검색 필터링 미작동

### 단계 1: 문제 재현 ✓ (DONE)
- [x] /scraps 페이지 접속
- [x] 검색박스에 "API" 입력
- [x] 모든 스크랩 그대로 표시됨 (필터링 안됨) 확인

### 단계 2: 네트워크 요청 확인
- [ ] 브라우저 DevTools → Network 탭 열기
- [ ] 검색박스에 "API" 입력
- [ ] 관찰 사항 기록:
  - [ ] GET 요청이 발생했는가? (예: `/api/v1/scraps?search=API`)
  - [ ] 요청 상태는? (200, 404, 500?)
  - [ ] 응답 데이터는?
  ```bash
  # 요청이 없으면 → 프론트엔드 문제
  # 요청이 있지만 상태 500 → 백엔드 에러
  # 요청 성공하지만 필터링 안됨 → UI 업데이트 문제
  ```

### 단계 3: 프론트엔드 코드 검사
- [ ] 파일 찾기
  ```bash
  find frontend/src -name "*Scrap*" -type f | head -10
  ```
- [ ] 검색 입력 핸들러 확인
  ```typescript
  // 찾을 코드 패턴:
  // - onChange 이벤트 핸들러
  // - 검색 API 호출
  // - setSearchResults() 또는 유사
  ```
- [ ] 검사 항목:
  - [ ] 검색 입력값 감지하는가?
  - [ ] API 요청을 보내는가?
  - [ ] 응답을 상태에 저장하는가?
  - [ ] UI에 반영하는가?

### 단계 4: 백엔드 검색 API 검사
- [ ] API 직접 호출 테스트
  ```bash
  # API 엔드포인트 확인 (일반적으로 /scraps?search=API)
  curl -s "https://memoir-api.duckdns.org/api/v1/scraps?search=API" \
    -H "Authorization: Bearer <토큰>"
  ```
- [ ] 응답 데이터 확인
  - [ ] 반환된 스크랩 수 (필터됨?)
  - [ ] "API" 포함된 항목만 있는가?

### 단계 5: 백엔드 검색 로직 검사
- [ ] 파일 찾기
  ```bash
  find backend/app -name "*scrap*" -type f | grep -E "(router|service|repository)"
  ```
- [ ] 검색 쿼리 파라미터 처리 확인
  ```python
  # 찾을 코드 패턴:
  # - @router.get("/")
  # - def get_scraps(search: str = Query(None), ...)
  # - 검색 로직
  ```
- [ ] 검사 항목:
  - [ ] `search` 파라미터를 받는가?
  - [ ] 검색 대상 (제목, 태그, 내용)?
  - [ ] 대소문자 구분?
  - [ ] 부분 일치 구현?

### 단계 6: 해결 및 배포
- [ ] 원인 파악 후 코드 수정
  - [ ] 프론트엔드: API 요청 추가 또는 수정
  - [ ] 백엔드: 검색 로직 구현 또는 수정
- [ ] 로컬 테스트
  ```bash
  # 프론트 + 백엔드 모두 실행
  # /scraps에서 "API" 검색
  # 필터된 결과 확인
  ```
- [ ] 커밋 및 배포
  ```bash
  git add frontend backend
  git commit -m "fix: scrap search filtering"
  git push origin dev
  # EC2 배포...
  ```
- [ ] 재테스트
  - [ ] /scraps 접속
  - [ ] "API" 검색
  - [ ] API 관련 스크랩만 표시 확인

---

## 📋 공통 체크리스트

### 코드 리뷰
- [ ] 수정된 코드가 기존 기능을 깨뜨리지 않는가?
- [ ] 에러 처리가 충분한가?
- [ ] 로깅이 추가되었는가?
- [ ] 타입 힌트가 정확한가? (Python)
- [ ] 변수명이 명확한가?

### 테스트
- [ ] 로컬 환경에서 재현 및 해결 확인
- [ ] 기존 데이터로 회귀 테스트
- [ ] 엣지 케이스 테스트 (빈 데이터, 특수문자 등)

### 배포
- [ ] EC2 서버에 정상 배포되었는가?
- [ ] Docker 컨테이너가 정상 실행되는가?
- [ ] 프론트엔드(Vercel)도 최신 코드로 배포되었는가?

### 최종 검증
- [ ] 프로덕션 환경에서 재테스트
- [ ] 다른 기능에 영향이 없는가?
- [ ] 성능이 저하되지 않았는가?

---

## 💬 커뮤니케이션

### 이슈 해결 후 보고
```markdown
Issue #6: RESOLVED
- 원인: [원인 설명]
- 해결: [해결 방법]
- 테스트: [테스트 결과]
- 커밋: [커밋 해시]
```

---

## 📞 문의사항

문제 발생 시:
1. 이 체크리스트의 해당 단계 다시 확인
2. EC2 로그 확인 (`docker logs memoir-backend`)
3. DevTools Network 탭 확인
4. Supabase 콘솔에서 데이터 확인

---

**체크리스트 업데이트: 2026-03-17**
