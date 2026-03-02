# backend/app/mcp_server.py
"""Memoir AI MCP (Model Context Protocol) 서버.

MCP란?
------
Model Context Protocol은 Anthropic이 설계한 표준 프로토콜로,
LLM이 외부 도구·데이터·컨텍스트에 접근하는 방식을 통일한다.

Claude Desktop, VS Code Extension, Cursor 등의 MCP 클라이언트가
이 서버에 연결해서 Memoir의 42개 도구를 직접 호출할 수 있다.

아키텍처:
---------
ReAct 에이전트 (채팅)  ─┐
MCP 클라이언트 (외부)  ─┼─→ 동일한 비즈니스 로직 (서비스 레이어)
Screen API (FastAPI)  ─┘

차이점:
- ReAct 에이전트: user_id는 RunnableConfig.configurable에서 자동 주입
- MCP 클라이언트: user_id를 각 tool 호출 시 명시적 파라미터로 전달
  → MCP는 stateless HTTP 세션 기반이라 컨텍스트 자동 주입이 없음

실행 방법:
----------
  # 개발 (포트 8001)
  cd backend
  python -m app.mcp_server

  # Claude Desktop 연결 설정 (~/.claude_desktop_config.json):
  {
    "mcpServers": {
      "memoir-ai": {
        "type": "http",
        "url": "http://localhost:8001/mcp"
      }
    }
  }

  # fastmcp CLI로 테스트
  fastmcp list http://localhost:8001/mcp
  fastmcp call http://localhost:8001/mcp search_scraps '{"user_id":"...", "query":"React"}'
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# FastMCP 서버 인스턴스 생성
# name: MCP 클라이언트가 식별하는 서버 이름
# instructions: 이 서버가 무엇을 할 수 있는지 LLM에게 설명하는 텍스트
mcp = FastMCP(
    name="Memoir AI",
    instructions=(
        "개인 지식 관리 앱 Memoir의 AI 도구 모음입니다. "
        "스크랩 검색, 일기 분석, 지식 그래프 탐색, 콘텐츠 처리, "
        "리포트 생성 등 42가지 도구를 제공합니다. "
        "모든 도구는 user_id 파라미터로 사용자별 데이터를 격리합니다."
    ),
    version="1.0.0",
)


# ===========================================================================
# 1. 검색 (Retrieval) 도구
# ===========================================================================


@mcp.tool
async def search_scraps(user_id: str, query: str, limit: int = 10) -> list[dict]:
    """사용자 스크랩을 하이브리드 검색(Dense + Sparse + Graph)으로 조회한다.

    Args:
        user_id: Supabase 사용자 UUID
        query: 검색 쿼리 (자연어)
        limit: 최대 반환 결과 수 (기본 10)
    """
    from app.agents.container import get_agent_container

    container = get_agent_container()
    results = await container.hybrid_search.search(
        user_id=UUID(user_id),
        query=query,
        limit=limit,
    )
    return [
        {
            "id": r.get("id", ""),
            "title": r.get("title", ""),
            "content_preview": (r.get("content") or "")[:300],
            "tags": r.get("tags") or [],
            "source_type": r.get("source_type", ""),
            "created_at": r.get("created_at", ""),
            "score": r.get("hybrid_score", 0.0),
        }
        for r in results
    ]


@mcp.tool
async def search_graph_entities(
    user_id: str,
    keyword: str,
    entity_type: str = "",
    limit: int = 10,
) -> list[dict]:
    """Knowledge Graph에서 키워드로 엔티티를 검색한다.

    Args:
        user_id: Supabase 사용자 UUID
        keyword: 엔티티 이름 검색 키워드
        entity_type: 필터링할 엔티티 타입 (예: "Person", "Concept"). 빈 문자열이면 전체
        limit: 최대 반환 결과 수 (기본 10)
    """
    from app.agents.container import get_agent_container

    container = get_agent_container()
    return await container.mindmap_repo.search_entities(
        keyword=keyword,
        user_id=user_id,
        entity_type=entity_type,
        limit=limit,
    )


@mcp.tool
async def get_graph_context(user_id: str, topic: str, depth: int = 2) -> dict:
    """Knowledge Graph에서 주제 엔티티와 연결된 관련 엔티티 컨텍스트를 조회한다.

    Args:
        user_id: Supabase 사용자 UUID (현재는 검증용, 그래프 자체는 공유)
        topic: 탐색 중심 엔티티 이름
        depth: 탐색 깊이 (기본 2)
    """
    from app.agents.container import get_agent_container

    _ = UUID(user_id)  # UUID 유효성 검증
    container = get_agent_container()
    related = await container.mindmap_repo.get_related_context(
        topic=topic,
        depth=depth,
    )
    return {"topic": topic, "related_entities": related}


# ===========================================================================
# 2. 일기 (Diary) 도구
# ===========================================================================


@mcp.tool
async def search_diaries(
    user_id: str,
    query: str,
    limit: int = 10,
) -> list[dict]:
    """사용자 일기를 키워드로 검색한다.

    Args:
        user_id: Supabase 사용자 UUID
        query: 검색 쿼리 (자연어)
        limit: 최대 반환 결과 수 (기본 10)
    """
    from app.agents.container import get_agent_container

    container = get_agent_container()
    return await container.diary_repo.search_diaries(
        user_id=UUID(user_id),
        query=query,
        limit=limit,
    )


@mcp.tool
async def get_diary_statistics(user_id: str) -> dict:
    """일기 작성 통계를 반환한다 (총 개수, 스트릭, 감정 분포).

    Args:
        user_id: Supabase 사용자 UUID
    """
    from app.agents.container import get_agent_container

    container = get_agent_container()
    return await container.diary_repo.get_diary_statistics(user_id=UUID(user_id))


# ===========================================================================
# 3. 스크랩 KB (Knowledge Base) 도구
# ===========================================================================


@mcp.tool
async def get_scrap_detail(user_id: str, scrap_id: str) -> dict:
    """스크랩의 전체 내용을 조회한다.

    Args:
        user_id: Supabase 사용자 UUID
        scrap_id: 스크랩 UUID
    """
    from app.agents.container import get_agent_container

    container = get_agent_container()
    return await container.scrap_repo.get_scrap_by_id(
        user_id=UUID(user_id),
        scrap_id=UUID(scrap_id),
    )


@mcp.tool
async def list_recent_scraps(
    user_id: str,
    limit: int = 20,
) -> list[dict]:
    """최근 저장된 스크랩 목록을 반환한다.

    Args:
        user_id: Supabase 사용자 UUID
        limit: 최대 반환 결과 수 (기본 20)
    """
    from app.agents.container import get_agent_container

    container = get_agent_container()
    return await container.scrap_repo.list_recent_scraps(
        user_id=UUID(user_id),
        limit=limit,
    )


# ===========================================================================
# 4. 분석 (Analysis) 도구
# ===========================================================================


@mcp.tool
async def get_community_insights(user_id: str) -> list[dict]:
    """지식 그래프에서 주제 클러스터와 커뮤니티 인사이트를 반환한다.

    Args:
        user_id: Supabase 사용자 UUID
    """
    from app.agents.container import get_agent_container

    container = get_agent_container()
    summaries = await container.community_summary.get_community_summaries(user_id)
    return summaries or []


@mcp.tool
async def get_knowledge_stats(user_id: str) -> dict:
    """지식베이스 전체 통계를 반환한다 (스크랩 수, 엔티티 수, 관계 수 등).

    Args:
        user_id: Supabase 사용자 UUID
    """
    from langchain_core.runnables import RunnableConfig

    from app.agents.tools.stats_tools import get_knowledge_stats as _tool

    config = RunnableConfig(configurable={"user_id": user_id})
    return await _tool.ainvoke({}, config=config)


# ===========================================================================
# 5. 콘텐츠 처리 (Content Processing) 도구
# ===========================================================================


@mcp.tool
async def classify_content(user_id: str, text: str) -> dict:
    """텍스트를 INSIGHT / FACT / SPAM 중 하나로 분류한다.

    MCP를 통해 저장 전 콘텐츠 품질 평가에 활용할 수 있다.

    Args:
        user_id: 인증 검증용 UUID
        text: 분류할 텍스트
    """
    from langchain_core.runnables import RunnableConfig

    from app.agents.tools.content_tools import classify_content as _tool

    _ = UUID(user_id)  # UUID 유효성 검증
    config = RunnableConfig(configurable={"user_id": user_id})
    return await _tool.ainvoke({"text": text}, config=config)


@mcp.tool
async def summarize_content(user_id: str, text: str) -> str:
    """텍스트를 한국어 2~3문장으로 요약한다.

    Args:
        user_id: 인증 검증용 UUID
        text: 요약할 텍스트
    """
    from langchain_core.runnables import RunnableConfig

    from app.agents.tools.content_tools import summarize_content as _tool

    _ = UUID(user_id)
    config = RunnableConfig(configurable={"user_id": user_id})
    return await _tool.ainvoke({"text": text}, config=config)


@mcp.tool
async def extract_tags(user_id: str, text: str) -> list[str]:
    """텍스트에서 키워드 태그를 추출한다.

    Args:
        user_id: 인증 검증용 UUID
        text: 태그를 추출할 텍스트
    """
    from langchain_core.runnables import RunnableConfig

    from app.agents.tools.content_tools import extract_tags as _tool

    _ = UUID(user_id)
    config = RunnableConfig(configurable={"user_id": user_id})
    return await _tool.ainvoke({"text": text}, config=config)


# ===========================================================================
# 6. 그래프 관리 (Graph Management) 도구
# ===========================================================================


@mcp.tool
async def extract_entities(user_id: str, text: str) -> list[dict]:
    """텍스트에서 엔티티(사람, 개념, 장소 등)를 추출한다.

    Args:
        user_id: 인증 검증용 UUID
        text: 엔티티를 추출할 텍스트
    """
    from langchain_core.runnables import RunnableConfig

    from app.agents.tools.graph_tools import extract_entities as _tool

    _ = UUID(user_id)
    config = RunnableConfig(configurable={"user_id": user_id})
    return await _tool.ainvoke({"text": text}, config=config)


@mcp.tool
async def get_hub_entities(user_id: str, limit: int = 10) -> list[dict]:
    """가장 많은 연결을 가진 허브 엔티티 목록을 반환한다.

    지식 그래프에서 중심적인 개념이나 사람을 파악하는 데 유용하다.

    Args:
        user_id: Supabase 사용자 UUID
        limit: 최대 반환 결과 수 (기본 10)
    """
    from langchain_core.runnables import RunnableConfig

    from app.agents.tools.graph_tools import get_hub_entities as _tool

    config = RunnableConfig(configurable={"user_id": user_id})
    return await _tool.ainvoke({"limit": limit}, config=config)


# ===========================================================================
# 7. 리포트 (Report) 도구
# ===========================================================================


@mcp.tool
async def generate_daily_digest(user_id: str) -> dict:
    """오늘의 활동 다이제스트와 AI 소크라테스 질문을 생성한다.

    캘린더 화면의 '오늘의 브리핑'에 해당하는 데이터를 반환한다.

    Args:
        user_id: Supabase 사용자 UUID
    """
    from langchain_core.runnables import RunnableConfig

    from app.agents.tools.report_tools import generate_daily_digest as _tool

    config = RunnableConfig(configurable={"user_id": user_id})
    return await _tool.ainvoke({}, config=config)


@mcp.tool
async def generate_daily_insights(user_id: str) -> list[dict]:
    """오늘의 패턴·행동 제안 인사이트를 생성한다.

    Args:
        user_id: Supabase 사용자 UUID
    """
    from langchain_core.runnables import RunnableConfig

    from app.agents.tools.report_tools import generate_daily_insights as _tool

    config = RunnableConfig(configurable={"user_id": user_id})
    return await _tool.ainvoke({}, config=config)


# ===========================================================================
# 서버 실행
# ===========================================================================


def run_mcp_server(host: str = "0.0.0.0", port: int = 8001) -> None:
    """MCP 서버를 HTTP transport로 실행한다.

    MCP transport 종류:
    - stdio: Claude Desktop 같은 로컬 클라이언트용 (stdin/stdout)
    - http:  원격 클라이언트, 웹훅, REST 기반 통합용
    - sse:   Server-Sent Events (구 방식, http로 대체됨)

    포트 8000: 메인 FastAPI 앱
    포트 8001: MCP 서버 (이 파일)
    """
    logger.info("Memoir AI MCP 서버 시작: http://%s:%d/mcp", host, port)
    mcp.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    # uvicorn으로 직접 실행하는 경우 ASGI 앱으로 마운트
    # mcp.run()은 내부적으로 uvicorn을 사용하므로 아래와 동일
    run_mcp_server()
