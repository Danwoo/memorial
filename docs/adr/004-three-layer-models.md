# ADR-004: DB row · 도메인 엔티티 · API DTO 3계층 분리

**Status**: Accepted
**Date**: 2026-04

## 컨텍스트

리팩토링 전: Repository가 `dict` 반환, Service도 `dict` 그대로 흘려보냄, Router에서
수동으로 `dict["id"]` 접근해 Pydantic response 모델 조립.

문제:
- 타입 안전성 0 — `dict["foo"]` 오타가 런타임 에러로
- 비즈니스 불변식(예: `tags`는 list, `mood`는 enum) 검증 위치가 산재
- DB 스키마 변경이 Service / Router까지 전파 (예: `user_id` 컬럼명 변경 시 다수 변경)

## 결정

**3계층 분리**:

```
DB row (dict, Supabase 반환)
  ↓ Repository._row_to_entity()
도메인 엔티티 (Pydantic, app/domain/)
  ↓ Router._entity_to_dto()
API DTO (Pydantic, app/schemas/)
```

각 계층의 책임:
- **DB row**: 인프라(Supabase/Kuzu)의 wire format
- **도메인 엔티티**: 비즈니스 불변식 강제 (Pydantic validation), Service 간 통신
- **API DTO**: 외부 계약 (frontend, 다른 서비스) — 외부 변경 시 도메인 보호

신설된 도메인 모델:
- Chat: `ChatSession`, `ChatMessageRecord`, `ChatSessionSummary`
- Diary: `DiaryEntry`
- Mindmap: `MindmapEntity`, `MindmapRelation`, `MindmapShortestPath`
- Scrap: 기존 `ScrapInDB` 그대로 활용

## 트레이드오프

### 1. 변환 비용 (3개 모델 인스턴스 생성)

- 각 요청마다 dict → 도메인 모델 → DTO 변환 = 객체 N개 생성.
- **답변**: 측정 결과, 단일 요청에서 변환 비용 < 1ms. 명확함이 성능 비용을 압도.
  핫 패스(매 초 수천 호출)였다면 다시 봐야 하지만 현 운영 패턴(개인 사용자)에서 무시 가능.

### 2. 분석성 메서드는 여전히 dict

- `DiaryRepository.get_diary_statistics`, `get_emotion_trend`, `list_diary_dates` 등은
  형태가 다양해서 dict 유지.
- **답변**: 분석성 응답은 ad-hoc 형태 — Pydantic 모델로 강제하면 매 분석마다 새 모델
  정의 부담. 운영 데이터로 가장 많이 쓰는 형태가 안정화되면 그때 모델화.

### 3. Mindmap의 `get_graph_data`는 D3 wire format 그대로

- `{"nodes": [...], "links": [...]}` 형태 — D3 호환.
- **답변**: 시각화 read-only 전용이고 5분 TTL 캐시. 도메인 모델로 변환 후 다시 dict
  직렬화하는 cost > 명확성 이득. 명시적 trade-off로 service docstring에 기록
  (`mindmap_service.py:get_visualization_data`).

## 검증

- `tests/test_domain_models.py` — 15+ 테스트로 frozen, 기본값, model_copy 검증
- `tests/integration/` — TestClient로 도메인 모델 → DTO 변환 contract 검증
