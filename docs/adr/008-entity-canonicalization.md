# ADR-008: 엔티티 canonicalization — 정적 dict 시작, 운영 데이터 보고 동적으로

**Status**: Accepted (1단계 정적, 향후 단계적 동적 전환 예정)
**Date**: 2026-05

## 컨텍스트

LLM이 prompt rule을 지키더라도 100% 정확하지 않다. 같은 개념을 다른 이름으로 추출:

- "리액트" / "ReactJS" / "react" / "React.js" → 모두 `React` 노드여야 함
- 안 그러면 그래프에 중복 노드, 시각화/shortest path 품질 저하

## 고려한 대안

| 접근 | 정확도 | 운영 부담 | 시작 비용 |
|------|--------|-----------|-----------|
| **prompt rule만 (이전)** | 모델 신뢰도에 100% 의존 | 없음 | 0 |
| **정적 alias dict (선택, 1단계)** | 등록된 동의어만 처리, 화이트리스트 | 사람이 직접 추가 | 50개 시드 |
| **Embedding similarity** | 의미적 유사 자동 매칭 | 임계값 튜닝, false positive 위험 | 임베딩 비용 |
| **LLM 분류 (cluster + canonical 선택)** | 가장 정확 | LLM 호출 비용 + 지연 | prompt 설계 |

## 결정

**1단계: 정적 alias dict + case-insensitive 화이트리스트** (`app/repositories/mindmap/_aliases.py`).

```python
_EXACT_ALIASES = {
    "리액트": "React", "ReactJS": "React",
    "타입스크립트": "TypeScript", "TS": "TypeScript",
    # ... 50개
}

_CASE_INSENSITIVE_CANONICAL = {
    name.lower(): name for name in {
        "React", "JavaScript", "TypeScript", "Python", ...
    }
}

def canonicalize_entity_name(name: str) -> str:
    stripped = name.strip()
    if stripped in _EXACT_ALIASES:
        return _EXACT_ALIASES[stripped]
    if stripped.lower() in _CASE_INSENSITIVE_CANONICAL:
        return _CASE_INSENSITIVE_CANONICAL[stripped.lower()]
    return stripped
```

`save_entities`/`save_relations` 진입에 자동 적용 (`mindmap/_storage.py`).

## 1단계 정직한 한계

- 50개 시드 화이트리스트는 운영 데이터 1만 노드를 못 따라간다.
- 새로운 분야(예: 의료, 법률) 진입 시 매핑 0.
- 사람이 직접 사전 추가하는 사용성 문제.

## 향후 단계 (트리거 + 마이그레이션 경로)

### 2단계 — 자동 cluster 추출 (트리거: 노드 1000+ 도달)
- 주기적 job (예: 일 1회) `cluster_similar_entities()`:
  1. KuzuDB에서 모든 Entity 이름 dump
  2. embedding으로 cosine similarity > 0.92인 노드 쌍 찾기
  3. LLM에 candidate 묶음 전달 — "이 중 같은 개념끼리 묶고 canonical 이름 선택"
  4. 결과를 `entity_alias_log` 테이블에 기록 (수동 검토 가능)
  5. 검토 통과 항목만 `_EXACT_ALIASES`에 반영 (자동 PR 또는 DB row)

### 3단계 — 실시간 lookup (트리거: 노드 10000+ 도달)
- `save_entities` 진입 시 embedding으로 유사 노드 즉시 찾음 → 사용자에게 confirm:
  "이건 React와 같은 의미인가요?" (UI 노출)

## 트레이드오프 / 알려진 한계

### 1. "왜 처음부터 embedding으로 안 했어?"

- 시작 단계에 false positive 위험 크고 (임계값 튜닝 = 운영 데이터 필요), 임베딩 호출 비용
  (매 저장마다 LLM call)이 부담.
- **대응**: 50개 시드 룰로 80%+ 케이스(JavaScript 생태계 + AI/ML + DB) 커버.
  운영 데이터 보고 false negative 사례 수집 후 2단계로 자동화 — 점진적 정교화.

### 2. "정적 dict 50개로 충분한가?"

- 솔직히 충분하지 않다. 새 분야 진입 시 즉시 한계.
- **대응**: 위 마이그레이션 경로 설계 완료. 2단계 자동화 코드는 작성 가능 — 데이터 없어
  아직 도입 안 함. ADR에 트리거 명시 (1000 노드).

### 3. "테스트는?"

- `tests/test_canonicalize.py` 8개 — 정확 일치 / case insensitive / passthrough / whitespace.
- 운영 데이터의 false positive/negative 측정은 데이터 모이고 가능.

## 결론

지금 상태는 **운영 데이터 0의 합리적 출발점**. 데이터 모이면 ADR-009로 superseded.
