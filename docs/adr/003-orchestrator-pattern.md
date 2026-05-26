# ADR-003: Cross-domain 흐름은 Orchestrator로만

**Status**: Accepted
**Date**: 2026-04

## 컨텍스트

다이어리 생성 endpoint는 다음 흐름을 수행해야 한다:

1. 다이어리 entry 저장 (`DiaryService`)
2. 다이어리 내용을 스크랩으로 적재 (`ScrapService` — **다른 도메인**)
3. Librarian agent로 엔티티/관계 추출 (LangGraph — **에이전트 layer**)

리팩토링 전:
- `diary_router.py`가 `ScrapService`와 `librarian_graph`를 직접 import해 백그라운드 task에서 호출
- `diary` prefix의 라우터가 `scrap`/`librarian`을 알게 됨 → 도메인 경계 무너짐

## 고려한 대안

| 옵션 | 의견 |
|------|------|
| **현 상태 유지 (router가 cross-domain)** | 도메인 경계 무너짐, router가 비대 |
| **`DiaryService`에 cross-domain 메서드 추가** | DiaryService가 ScrapService에 의존 → 양방향 결합 위험 |
| **Event-driven (메시지 큐)** | 인프라 부담 (Redis Streams 등), 작은 앱에 over-engineering |
| **Orchestrator 클래스 (선택)** | cross-domain 흐름의 위치를 한곳에 명시, service들은 자기 도메인만 알면 됨 |

## 결정

`app/orchestrators/` 폴더 신설, **명시적 Orchestrator 클래스**가 다중 도메인을 조율.

```python
# app/orchestrators/diary_orchestrator.py
class DiaryOrchestrator:
    def __init__(self, scrap_service: ScrapService):
        self.scrap_service = scrap_service

    async def process_diary_with_librarian(
        self, diary_id: str, content: str, user_id: str,
    ) -> None:
        scrap = await self.scrap_service.create_scrap(...)
        result = await librarian_graph.ainvoke(...)
```

원칙:
- **같은 prefix끼리는 직접 의존 가능**
- **Cross-domain은 반드시 Orchestrator 경유**
- Orchestrator는 도메인 service들을 조립할 뿐, 자기 비즈니스 로직은 갖지 않음 (조율자)

## 트레이드오프

### 1. "Saga" 패턴까지는 안 감

- 단계별 실패 시 보상 트랜잭션(rollback) 없음.
- **대응**: 현 flow는 **graceful degradation으로 충분**. 스크랩 적재 실패해도 다이어리는
  이미 저장됐고, librarian은 향후 backfill로 재처리 가능. 진짜 Saga는 결제/송금처럼
  강한 일관성 요구되는 곳에 필요.

### 2. Orchestrator가 자라면 결국 비대해짐

- 향후 더 많은 cross-domain 흐름이 추가되면 한 Orchestrator에 메서드 N개.
- **대응**: 흐름 단위로 분할 (`DiaryOrchestrator`, `ScrapIngestOrchestrator` 등).
  지금은 1개 — 명확.

### 3. Background task vs sync

- `process_diary_with_librarian`은 FastAPI `BackgroundTasks`로 fire-and-forget.
- 사용자에게 즉시 응답하되 librarian 결과는 비동기로 적재.
- **약점**: 백그라운드 실패 시 사용자가 모름. 모니터링 필요.
- **대응**: `logger.exception`으로 보존. 운영 환경에서는 Sentry 같은 alerting 추가.
