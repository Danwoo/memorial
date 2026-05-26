"""엔티티 alias 자동 발견 — ADR-008 2단계 마이그레이션용 스켈레톤.

운영 데이터가 모이면 (트리거: 노드 1000+ 도달) 이 모듈을 활용해 자동으로
유사 엔티티 클러스터를 발견하고 운영자 검토 후 `_aliases.py`에 추가하는 흐름.

현재는 호출 사이트 없음 (데이터 부족). 데이터 모이면 다음 흐름:
    1. 스케줄러 job (일 1회)이 `discover_alias_candidates(repo)` 호출
    2. 결과를 `entity_alias_candidates` 테이블에 기록
    3. 관리자 UI에서 검토 → 승인 시 `_EXACT_ALIASES`에 동적 추가
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 임계값 — 후보 발견 정밀도/recall trade-off (운영 데이터로 튜닝 예정)
EMBEDDING_SIMILARITY_THRESHOLD = 0.92
MIN_CO_OCCURRENCE = 2  # 같은 메모리에 함께 등장한 횟수
MAX_CANDIDATES_PER_RUN = 50  # LLM 검증 비용 제어


@dataclass(frozen=True)
class AliasCandidate:
    """발견된 잠재적 alias 쌍."""

    name_a: str
    name_b: str
    similarity: float  # 0.0~1.0
    co_occurrence: int  # 같은 메모리에 함께 등장한 횟수
    suggested_canonical: str | None = None  # LLM이 추천한 canonical (둘 중 하나)


async def discover_alias_candidates(
    mindmap_repo,
    vector_repo,
    limit: int = MAX_CANDIDATES_PER_RUN,
) -> list[AliasCandidate]:
    """엔티티 이름 임베딩 유사도 + 동시 등장 빈도로 alias 후보 탐색.

    아직 호출 사이트 없음. ADR-008 2단계 진입 시 활성화.

    Args:
        mindmap_repo: 엔티티 이름/관계 조회
        vector_repo: 이름 임베딩 생성
        limit: 한 번에 추출할 최대 후보 수 (LLM 검증 비용 제어)

    Returns:
        검토할 후보 쌍 리스트. 각 쌍은 사람/LLM 검증을 거쳐야 alias로 등록됨.
    """
    # 1. 모든 엔티티 이름 dump (mindmap_repo가 메서드 추가 필요)
    # 2. 이름별 임베딩 생성 (vector_repo.embed_documents)
    # 3. 임베딩 유사도 매트릭스 (코사인) — 임계값 초과 쌍 추출
    # 4. 각 쌍의 동시 등장 빈도 확인 (Memory에서 함께 mention된 횟수)
    # 5. LLM에 candidate 묶음 전달 — "이 중 같은 의미끼리 묶고 canonical 이름 선택"
    # 6. AliasCandidate 리스트 반환

    logger.info("discover_alias_candidates는 아직 활성화되지 않았다 (ADR-008 2단계 대기)")
    return []


# 활성화 시 추가 검증 항목 (체크리스트):
# - false positive 비율 측정 (운영자 검토 결과 추적)
# - canonical 이름 선택 정책 (영문 우선 / 사용 빈도 높은 쪽 / LLM 판단)
# - 자동 적용 vs 수동 승인 (안전을 위해 수동 권장)
