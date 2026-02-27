import logging

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from app.agents.socrates.context import SocratesContext
from app.agents.socrates.state import SocratesState

logger = logging.getLogger(__name__)

# 다이어리 감정 추이 조회 기간 (일)
DIARY_EMOTION_DAYS = 7
# 다이어리 미리보기 길이
DIARY_PREVIEW_LENGTH = 600
# 최근 다이어리 조회 수
DIARY_RECENT_LIMIT = 5


async def _fetch_recent_diary_emotions(user_id: str, diary_repo) -> str:
    """최근 7일 다이어리 감정 추이 포맷 문자열로 반환."""
    try:
        from datetime import UTC, datetime, timedelta

        end_dt = datetime.now(UTC)
        start_dt = end_dt - timedelta(days=DIARY_EMOTION_DAYS)
        diaries = await diary_repo.get_diaries_by_date_range(
            user_id,
            start_dt.isoformat(),
            end_dt.isoformat(),
            limit=DIARY_RECENT_LIMIT,
        )
        if not diaries:
            # 날짜 범위 조회 실패 시 최근 N개로 폴백
            diaries = await diary_repo.get_diaries(user_id, limit=DIARY_RECENT_LIMIT)

        if not diaries:
            return ""

        lines = []
        for d in diaries:
            date = str(d.get("created_at", ""))[:10]
            mood = d.get("mood", "")
            tags = ", ".join(d.get("tags", []) or [])
            content_preview = (d.get("content") or "")[:DIARY_PREVIEW_LENGTH]
            line = f"[{date}] 감정: {mood or '기록 없음'}"
            if tags:
                line += f" | 태그: {tags}"
            line += f"\n{content_preview}"
            lines.append(line)

        return "\n\n".join(lines)
    except Exception:
        logger.exception("diary_deep_retrieval: 감정 추이 조회 실패")
        return ""


async def _fetch_current_diary_context(source_context: dict | None) -> str:
    """source_context에서 현재 작성 중인 다이어리 본문 추출."""
    if not source_context:
        return ""
    if source_context.get("type") != "diary":
        return ""

    title = source_context.get("title", "")
    content_preview = source_context.get("content_preview", "")
    mood = source_context.get("mood", "")
    tags = source_context.get("tags", [])

    if not (title or content_preview):
        return ""

    parts = ["**현재 다이어리 내용:**"]
    if title:
        parts.append(f"제목: {title}")
    if mood:
        parts.append(f"감정: {mood}")
    if tags:
        parts.append(f"태그: {', '.join(tags)}")
    if content_preview:
        parts.append(f"\n{content_preview}")

    return "\n".join(parts)


async def diary_deep_retrieval_node(state: SocratesState, runtime: Runtime[SocratesContext]) -> dict:
    """다이어리 전문 컨텍스트 수집 노드.

    Socrates 에이전트 전용: 현재 작성 중인 다이어리 본문 + 최근 7일 감정 추이를 수집한다.
    결과는 state의 diary_context에 저장되어 socrates_assembly에서 활용된다.
    """
    writer = get_stream_writer()
    writer({"node": "diary_deep_retrieval", "status": "started"})

    user_id = state["user_id"]
    source_context = state.get("source_context")
    diary_repo = runtime.context.diary_repo

    current_diary, emotion_trend = await __import__("asyncio").gather(
        _fetch_current_diary_context(source_context),
        _fetch_recent_diary_emotions(user_id, diary_repo),
        return_exceptions=True,
    )

    if isinstance(current_diary, Exception):
        logger.warning("current_diary fetch 예외: %s", current_diary)
        current_diary = ""
    if isinstance(emotion_trend, Exception):
        logger.warning("emotion_trend fetch 예외: %s", emotion_trend)
        emotion_trend = ""

    # diary_context에 합산 저장
    diary_context_parts = []
    if current_diary:
        diary_context_parts.append(current_diary)
    if emotion_trend:
        diary_context_parts.append(f"**최근 {DIARY_EMOTION_DAYS}일 다이어리 감정 추이:**\n{emotion_trend}")

    diary_context = "\n\n".join(diary_context_parts)

    writer({"node": "diary_deep_retrieval", "status": "done"})

    return {"diary_context": diary_context}
