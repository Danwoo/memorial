# backend/app/agents/tools/kb_tools.py
"""지식 베이스(스크랩) 관리 도구 모음 — 스크랩 조회, 필터링, 메타데이터 업데이트."""

from typing import Any
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.agents.container import get_agent_container
from app.agents.tools._context import get_user_id


@tool
async def get_scrap_detail(
    scrap_id: str,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """특정 스크랩의 전체 내용을 조회한다.

    Args:
        scrap_id: 조회할 스크랩 UUID 문자열

    Returns:
        id, title, content, summary, tags, source_type, source_url, created_at 필드를 가진 dict
        (스크랩이 없으면 빈 dict 반환)
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    try:
        scrap = await container.scrap_repo.get_by_id(
            memory_id=UUID(scrap_id),
            user_id=UUID(user_id),
        )
    except (ValueError, Exception):
        return {}

    if not scrap:
        return {}

    return {
        "id": str(scrap.id),
        "title": scrap.title,
        "content": scrap.content,
        "summary": scrap.summary or "",
        "tags": scrap.tags or [],
        "source_type": scrap.source_type,
        "source_url": scrap.source_url or "",
        "created_at": scrap.created_at.isoformat() if scrap.created_at else "",
    }


@tool
async def list_recent_scraps(
    limit: int = 10,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """사용자의 최근 스크랩 목록을 반환한다.

    Args:
        limit: 반환할 최대 스크랩 수 (기본 10)

    Returns:
        id, title, summary, tags, source_type, created_at 필드를 가진 dict 리스트
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    items, _ = await container.scrap_repo.get_by_user(
        user_id=UUID(user_id),
        page=1,
        limit=limit,
        sort_by="created_at",
        sort_order="desc",
    )

    return [
        {
            "id": str(s.id),
            "title": s.title,
            "summary": s.summary or "",
            "tags": s.tags or [],
            "source_type": s.source_type,
            "created_at": s.created_at.isoformat() if s.created_at else "",
        }
        for s in items
    ]


@tool
async def list_scraps_by_tag(
    tag: str,
    limit: int = 20,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """특정 태그가 붙은 스크랩 목록을 반환한다.

    Args:
        tag: 필터링할 태그 문자열
        limit: 반환할 최대 스크랩 수 (기본 20)

    Returns:
        id, title, summary, tags, source_type, created_at 필드를 가진 dict 리스트
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    items, _ = await container.scrap_repo.get_by_user(
        user_id=UUID(user_id),
        page=1,
        limit=limit,
        tags=[tag],
        sort_by="created_at",
        sort_order="desc",
    )

    return [
        {
            "id": str(s.id),
            "title": s.title,
            "summary": s.summary or "",
            "tags": s.tags or [],
            "source_type": s.source_type,
            "created_at": s.created_at.isoformat() if s.created_at else "",
        }
        for s in items
    ]


@tool
async def update_scrap_metadata(
    scrap_id: str,
    tags: list[str] | None = None,
    summary: str | None = None,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """스크랩의 태그 또는 요약을 업데이트한다.

    Args:
        scrap_id: 업데이트할 스크랩 UUID 문자열
        tags: 새로운 태그 목록 (None이면 변경 안 함)
        summary: 새로운 요약 텍스트 (None이면 변경 안 함)

    Returns:
        updated 성공 여부와 scrap_id 필드를 가진 dict
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    if tags is None and summary is None:
        return {"updated": False, "scrap_id": scrap_id, "reason": "변경할 필드가 없습니다."}

    try:
        fields: dict[str, Any] = {}
        if tags is not None:
            fields["tags"] = tags
        if summary is not None:
            fields["summary"] = summary

        result = await container.scrap_repo.update_fields(
            memory_id=UUID(scrap_id),
            user_id=UUID(user_id),
            **fields,
        )
        return {"updated": result is not None, "scrap_id": scrap_id}
    except (ValueError, Exception):
        return {"updated": False, "scrap_id": scrap_id}
