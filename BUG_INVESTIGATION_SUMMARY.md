# 🔴 Memoir 서비스 - 긴급 버그 조사 요약

**작성일**: 2026-03-17
**상태**: 근본 원인 파악 완료, 해결 대기 중

---

## 핵심 발견사항

### Issue #6: 다이어리 좌측 화살표 네비게이션 실패 (Black Screen)

#### 증상
- 다이어리 페이지에서 좌측 화살표 클릭 → 검은 화면으로 로딩됨
- URL은 정상 변경됨 (`/diary?date=2026-03-16`)
- 페이지는 응답하지 않음

#### 근본 원인 (조사 결과)
**프론트엔드가 두 개의 API를 대기 중인데, 하나가 응답하지 않음:**

```
1. GET /api/v1/diaries/by-date/2026-03-16
   ✅ 상태: 200 OK (성공)

2. GET /api/v1/digest/date/2026-03-16
   ❌ 상태: PENDING (응답 없음 - 타임아웃)
```

프론트엔드가 두 API의 응답을 모두 기다리는데, digest API가 응답하지 않아서 페이지가 로딩 상태에서 멈춤.

#### 해결을 위한 디버깅 체크리스트

**Step 1: 백엔드 로그 확인**
```bash
# EC2 서버 접속
ssh -i <key_file> ubuntu@15.165.17.222

# Docker 컨테이너 로그 확인
cd /home/ubuntu/memorial
docker logs memoir-backend | tail -200 | grep -i "digest\|error\|exception"

# 또는 실시간 로그 확인
docker logs -f memoir-backend
```

**Step 2: 백엔드 코드 검사**
- 파일: `backend/app/routers/digest_router.py` (또는 해당 엔드포인트)
- 확인 사항:
  - 쿼리 성능 (DB 쿼리가 느린가?)
  - 타임아웃 설정 (기본값: 30초, 너무 짧은가?)
  - 예외 처리 (에러가 발생했는데 catch되지 않았나?)
  - 인증/권한 확인 (user_id 검증 실패?)

**Step 3: 데이터베이스 확인**
- Supabase 콘솔에서 해당 날짜의 데이터 확인
- 쿼리 성능 테스트:
  ```sql
  -- 특정 날짜의 digest 데이터 확인
  SELECT * FROM digests WHERE user_id = '<user_id>' AND date = '2026-03-16';
  ```

**Step 4: 로컬 환경에서 재현**
```bash
# 직접 API 호출 테스트
curl -s https://memoir-api.duckdns.org/api/v1/digest/date/2026-03-16 \
  -H "Authorization: Bearer <access_token>" | jq .
```

---

### Issue #7: 스크랩 검색 필터링 미작동

#### 증상
- 검색박스에 "API" 입력
- 기대: API 관련 스크랩만 필터링 표시
- 실제: 모든 스크랩 그대로 표시 (필터링 안됨)

#### 근본 원인 (조사 대기)
**가능한 원인:**
1. 프론트엔드 검색 입력 이벤트가 백엔드로 전송되지 않음
2. 백엔드 검색 API가 응답하지 않음
3. 프론트연에서 검색 결과를 UI에 반영하지 않음

#### 해결을 위한 디버깅 체크리스트

**Step 1: 네트워크 요청 확인**
- 브라우저 DevTools → Network 탭
- 검색박스에 "API" 입력
- 관찰 사항:
  - GET 요청이 발생하는가? (예: `/api/v1/scraps?search=API`)
  - 요청 상태는? (200, 404, 500?)
  - 응답 데이터는? (필터된 결과 수?)

**Step 2: 프론트엔드 코드 검사**
- 파일: `frontend/src/pages/Scraps.tsx` (또는 ScrapsView 컴포넌트)
- 확인 사항:
  - 검색 입력값 감지 (onChange 핸들러)
  - 입력값을 API로 전송하는가?
  - 응답 결과를 상태로 업데이트하는가?
  - UI에 필터된 결과를 표시하는가?

**Step 3: 백엔드 검색 API 테스트**
```bash
# 직접 API 호출 테스트
curl -s "https://memoir-api.duckdns.org/api/v1/scraps?search=API" \
  -H "Authorization: Bearer <access_token>" | jq '.data | length'
```

**Step 4: 백엔드 검색 로직 확인**
- 파일: `backend/app/routers/scrap_router.py` (또는 검색 엔드포인트)
- 확인 사항:
  - `search` 쿼리 파라미터 처리
  - 검색 로직 (제목, 태그, 내용 등 검색 대상)
  - 대소문자 구분 여부
  - 부분 일치 vs 정확 일치

---

## 추가 테스트 결과

### ✅ 정상 작동 확인된 기능

| 기능 | 상태 | 비고 |
|------|------|------|
| 캘린더 월 네비게이션 | ✅ | 좌/우 화살표 정상 |
| 다이어리 리치 텍스트 에디터 | ✅ | 포맷팅 도구 완벽 |
| 스크랩 필터 (전체/웹/메모) | ✅ | 필터 버튼 작동 |
| 스크랩 정렬 | ✅ | 최신순/오래된순 전환 |
| 타임라인 뷰 | ✅ | 세로 레이아웃 정상 |
| 데이터 내보내기 (JSON) | ✅ | 다운로드 시작 확인 |
| 마인드맵 줌 기능 | ✅ | 마우스 휠 스크롤 작동 |
| 마인드맵 드래그 | ✅ | 뷰 이동 가능 |

---

## 다음 단계

1. **개발팀**: 위의 디버깅 체크리스트 실행
2. **QA팀**: 해결 후 재테스트
3. **운영팀**: 해결 후 EC2 서버에 배포

---

## 참고 자료

- **EC2 IP**: 15.165.17.222
- **백엔드 Docker**: `/home/ubuntu/memorial/docker-compose.yml`
- **데이터베이스**: Supabase (otzqnucgfrlbqyyhksgo)
- **테스트 데이터**: 다이어리 99개, 스크랩 117개 (March 1-17, 2026)
