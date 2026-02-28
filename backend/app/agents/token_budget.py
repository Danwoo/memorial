import logging

logger = logging.getLogger(__name__)

# 총 컨텍스트 최대 문자 수 (~6.5k tokens)
MAX_CONTEXT_CHARS = 20_000

# 절삭 우선순위: 인덱스 높을수록 먼저 절삭
SECTION_PRIORITY = [
    "formatted_memories",
    "diary_context",
    "contradiction_context",
    "graph_context",
    "community_context",
    "connection_suggestion",
    "previous_session_context",
    "topic_session_context",
]


def enforce_context_budget(
    sections: dict[str, str],
    budget: int = MAX_CONTEXT_CHARS,
) -> dict[str, str]:
    """총합이 budget을 초과할 경우 우선순위 낮은 섹션부터 절삭.

    sections: {섹션명: 내용} — SECTION_PRIORITY에 없는 키는 항상 보존.
    반환: 절삭된 dict (원본 변경 없음).
    """
    result = dict(sections)
    total = sum(len(v) for v in result.values())
    if total <= budget:
        return result

    # 우선순위 낮은 것부터 절삭 (리스트 역순)
    for key in reversed(SECTION_PRIORITY):
        if total <= budget:
            break
        if key not in result or not result[key]:
            continue
        excess = total - budget
        current_len = len(result[key])
        if current_len <= excess:
            logger.debug("컨텍스트 예산 초과 — %s 전체 제거 (%d chars)", key, current_len)
            result[key] = ""
            total -= current_len
        else:
            keep = current_len - excess
            logger.debug("컨텍스트 예산 초과 — %s 절삭 %d→%d chars", key, current_len, keep)
            result[key] = result[key][:keep]
            total -= excess

    return result
