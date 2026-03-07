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
이 서버는 단일 진실 공급원(Single Source of Truth)이다.

외부 MCP 클라이언트 (Claude Desktop, VS Code):
    @mcp.tool → 명시적 user_id 파라미터 → 서비스 레이어

내부 ReAct 에이전트 (langchain-mcp-adapters):
    MCPToolLoader → get_tools() → user_id 자동 주입 래퍼 → 이 MCP 서버 호출

두 경로 모두 동일한 @mcp.tool 비즈니스 로직을 사용한다.

차이점:
- 외부 MCP 클라이언트: user_id를 각 tool 호출 시 명시적 파라미터로 전달
- 내부 ReAct 에이전트: MCPToolLoader가 user_id를 RunnableConfig에서 추출하여 주입

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
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)

# FastMCP 서버 인스턴스 생성
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


def _make_config(user_id: str) -> RunnableConfig:
    """user_id를 configurable에 담은 RunnableConfig를 생성한다."""
    return RunnableConfig(configurable={"user_id": user_id})


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
    from app.agents.tools.retrieval_tools import search_scraps as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"query": query, "limit": limit}, config=_make_config(user_id))


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
    from app.agents.tools.retrieval_tools import search_graph_entities as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke(
        {"keyword": keyword, "entity_type": entity_type, "limit": limit},
        config=_make_config(user_id),
    )


@mcp.tool
async def get_graph_context(user_id: str, topic: str, depth: int = 2) -> dict:
    """Knowledge Graph에서 주제 엔티티와 연결된 관련 엔티티 컨텍스트를 조회한다.

    Args:
        user_id: Supabase 사용자 UUID
        topic: 탐색 중심 엔티티 이름
        depth: 탐색 깊이 (기본 2)
    """
    from app.agents.tools.retrieval_tools import get_graph_context as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"topic": topic, "depth": depth}, config=_make_config(user_id))


# ===========================================================================
# 2. 일기 (Diary) 도구
# ===========================================================================


@mcp.tool
async def search_diaries(user_id: str, query: str, limit: int = 10) -> list[dict]:
    """사용자 일기를 텍스트 쿼리로 검색한다.

    Args:
        user_id: Supabase 사용자 UUID
        query: 검색 키워드 (제목 또는 본문 포함 여부 확인)
        limit: 최대 반환 결과 수 (기본 10)
    """
    from app.agents.tools.diary_tools import search_diaries as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"query": query, "limit": limit}, config=_make_config(user_id))


@mcp.tool
async def get_diary_detail(user_id: str, diary_id: str) -> dict:
    """특정 일기의 전체 내용을 조회한다.

    Args:
        user_id: Supabase 사용자 UUID
        diary_id: 조회할 일기의 UUID 문자열
    """
    from app.agents.tools.diary_tools import get_diary_detail as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"diary_id": diary_id}, config=_make_config(user_id))


@mcp.tool
async def get_diary_statistics(user_id: str) -> dict:
    """일기 작성 통계를 반환한다 (총 개수, 감정 분포).

    Args:
        user_id: Supabase 사용자 UUID
    """
    from app.agents.tools.diary_tools import get_diary_statistics as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({}, config=_make_config(user_id))


@mcp.tool
async def get_emotion_trend(user_id: str, days: int = 7) -> list[dict]:
    """최근 N일간 작성된 일기의 감정 추세를 반환한다.

    Args:
        user_id: Supabase 사용자 UUID
        days: 조회 기간 (일 단위, 기본 7일)
    """
    from app.agents.tools.diary_tools import get_emotion_trend as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"days": days}, config=_make_config(user_id))


@mcp.tool
async def list_diary_dates(user_id: str, limit: int = 30) -> list[str]:
    """사용자가 일기를 작성한 날짜 목록을 반환한다.

    Args:
        user_id: Supabase 사용자 UUID
        limit: 최대 반환 날짜 수 (기본 30)
    """
    from app.agents.tools.diary_tools import list_diary_dates as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"limit": limit}, config=_make_config(user_id))


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
    from app.agents.tools.kb_tools import get_scrap_detail as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"scrap_id": scrap_id}, config=_make_config(user_id))


@mcp.tool
async def list_recent_scraps(user_id: str, limit: int = 20) -> list[dict]:
    """최근 저장된 스크랩 목록을 반환한다.

    Args:
        user_id: Supabase 사용자 UUID
        limit: 최대 반환 결과 수 (기본 20)
    """
    from app.agents.tools.kb_tools import list_recent_scraps as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"limit": limit}, config=_make_config(user_id))


@mcp.tool
async def list_scraps_by_tag(user_id: str, tag: str, limit: int = 20) -> list[dict]:
    """특정 태그가 붙은 스크랩 목록을 반환한다.

    Args:
        user_id: Supabase 사용자 UUID
        tag: 필터링할 태그 문자열
        limit: 반환할 최대 스크랩 수 (기본 20)
    """
    from app.agents.tools.kb_tools import list_scraps_by_tag as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"tag": tag, "limit": limit}, config=_make_config(user_id))


@mcp.tool
async def update_scrap_metadata(
    user_id: str,
    scrap_id: str,
    tags: list[str] | None = None,
    summary: str | None = None,
) -> dict:
    """스크랩의 태그 또는 요약을 업데이트한다.

    Args:
        user_id: Supabase 사용자 UUID
        scrap_id: 업데이트할 스크랩 UUID 문자열
        tags: 새로운 태그 목록 (None이면 변경 안 함)
        summary: 새로운 요약 텍스트 (None이면 변경 안 함)
    """
    from app.agents.tools.kb_tools import update_scrap_metadata as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke(
        {"scrap_id": scrap_id, "tags": tags, "summary": summary},
        config=_make_config(user_id),
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
    from app.agents.tools.analysis_tools import get_community_insights as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({}, config=_make_config(user_id))


@mcp.tool
async def find_connections(user_id: str, topic1: str, topic2: str) -> dict:
    """두 주제 사이의 지식 연결 경로를 탐색한다.

    Args:
        user_id: Supabase 사용자 UUID
        topic1: 첫 번째 주제 또는 엔티티 이름
        topic2: 두 번째 주제 또는 엔티티 이름
    """
    from app.agents.tools.analysis_tools import find_connections as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"topic1": topic1, "topic2": topic2}, config=_make_config(user_id))


@mcp.tool
async def get_entity_timeline(user_id: str, entity_name: str, limit: int = 10) -> list[dict]:
    """특정 엔티티가 등장한 스크랩·일기 항목을 시간순으로 반환한다.

    Args:
        user_id: Supabase 사용자 UUID
        entity_name: 조회할 엔티티 이름
        limit: 최대 반환 항목 수 (기본 10)
    """
    from app.agents.tools.analysis_tools import get_entity_timeline as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"entity_name": entity_name, "limit": limit}, config=_make_config(user_id))


@mcp.tool
async def get_content_timeline(user_id: str, topic: str, days: int = 30) -> list[dict]:
    """특정 주제와 관련된 스크랩·일기를 시간순으로 반환한다.

    Args:
        user_id: Supabase 사용자 UUID
        topic: 검색할 주제 키워드
        days: 조회 기간 (일 단위, 기본 30일)
    """
    from app.agents.tools.analysis_tools import get_content_timeline as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"topic": topic, "days": days}, config=_make_config(user_id))


@mcp.tool
async def compare_content(user_id: str, text1: str, text2: str) -> dict:
    """두 텍스트의 유사도와 주요 차이점을 비교 분석한다.

    Args:
        user_id: Supabase 사용자 UUID (인증 검증용)
        text1: 첫 번째 텍스트
        text2: 두 번째 텍스트
    """
    from app.agents.tools.analysis_tools import compare_content as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"text1": text1, "text2": text2}, config=_make_config(user_id))


# ===========================================================================
# 5. 통계 (Stats) 도구
# ===========================================================================


@mcp.tool
async def get_knowledge_stats(user_id: str) -> dict:
    """지식베이스 전체 통계를 반환한다 (스크랩 수, 엔티티 수, 관계 수 등).

    Args:
        user_id: Supabase 사용자 UUID
    """
    from app.agents.tools.stats_tools import get_knowledge_stats as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({}, config=_make_config(user_id))


@mcp.tool
async def get_topic_distribution(user_id: str, limit: int = 10) -> list[dict]:
    """스크랩 태그 빈도 분포를 반환한다.

    Args:
        user_id: Supabase 사용자 UUID
        limit: 반환할 상위 태그 수 (기본 10)
    """
    from app.agents.tools.stats_tools import get_topic_distribution as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"limit": limit}, config=_make_config(user_id))


@mcp.tool
async def get_activity_streak(user_id: str) -> dict:
    """사용자의 다이어리 작성 활동 스트릭을 반환한다.

    Args:
        user_id: Supabase 사용자 UUID
    """
    from app.agents.tools.stats_tools import get_activity_streak as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({}, config=_make_config(user_id))


# ===========================================================================
# 6. 콘텐츠 처리 (Content Processing) 도구
# ===========================================================================


@mcp.tool
async def classify_content(user_id: str, text: str) -> dict:
    """텍스트를 INSIGHT / FACT / SPAM 중 하나로 분류한다.

    Args:
        user_id: 인증 검증용 UUID
        text: 분류할 텍스트
    """
    from app.agents.tools.content_tools import classify_content as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"text": text}, config=_make_config(user_id))


@mcp.tool
async def summarize_content(user_id: str, text: str) -> str:
    """텍스트를 한국어 2~3문장으로 요약한다.

    Args:
        user_id: 인증 검증용 UUID
        text: 요약할 텍스트
    """
    from app.agents.tools.content_tools import summarize_content as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"text": text}, config=_make_config(user_id))


@mcp.tool
async def extract_tags(user_id: str, text: str, max_tags: int = 5) -> list[str]:
    """텍스트에서 키워드 태그를 추출한다.

    Args:
        user_id: 인증 검증용 UUID
        text: 태그를 추출할 텍스트
        max_tags: 최대 태그 수 (기본 5)
    """
    from app.agents.tools.content_tools import extract_tags as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"text": text, "max_tags": max_tags}, config=_make_config(user_id))


@mcp.tool
async def analyze_sentiment(user_id: str, text: str) -> dict:
    """텍스트의 감정(긍정/부정/중립)과 구체적인 감정 상태, 강도를 분석한다.

    Args:
        user_id: 인증 검증용 UUID
        text: 감정을 분석할 텍스트
    """
    from app.agents.tools.content_tools import analyze_sentiment as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"text": text}, config=_make_config(user_id))


@mcp.tool
async def inline_edit(
    user_id: str,
    text: str,
    action: str = "polish",
) -> str:
    """텍스트를 지정된 방식으로 인라인 편집한다.

    Args:
        user_id: 인증 검증용 UUID
        text: 편집할 원문 텍스트
        action: 편집 방식 (expand/shorten/polish/formal/casual, 기본 polish)
    """
    from app.agents.tools.content_tools import inline_edit as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"text": text, "action": action}, config=_make_config(user_id))


# ===========================================================================
# 7. 그래프 관리 (Graph Management) 도구
# ===========================================================================


@mcp.tool
async def extract_entities(user_id: str, text: str) -> list[dict]:
    """텍스트에서 엔티티(사람, 개념, 장소 등)를 추출한다.

    Args:
        user_id: 인증 검증용 UUID
        text: 엔티티를 추출할 텍스트
    """
    from app.agents.tools.graph_tools import extract_entities as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"text": text}, config=_make_config(user_id))


@mcp.tool
async def extract_relations(user_id: str, text: str, entities: list[str]) -> list[dict]:
    """텍스트에서 엔티티 간 관계를 추출한다.

    Args:
        user_id: 인증 검증용 UUID
        text: 관계를 추출할 텍스트
        entities: 관계를 분석할 엔티티 이름 목록
    """
    from app.agents.tools.graph_tools import extract_relations as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"text": text, "entities": entities}, config=_make_config(user_id))


@mcp.tool
async def save_to_graph(
    user_id: str,
    source_id: str,
    source_type: str,
    entities: list[dict],
    relations: list[dict],
) -> dict:
    """추출된 엔티티와 관계를 KuzuDB 지식 그래프에 저장한다.

    Args:
        user_id: Supabase 사용자 UUID
        source_id: 출처 스크랩 또는 다이어리 ID
        source_type: "scrap" 또는 "diary"
        entities: name, type 필드를 가진 엔티티 dict 목록
        relations: source, rel_type, target 필드를 가진 관계 dict 목록
    """
    from app.agents.tools.graph_tools import save_to_graph as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke(
        {
            "source_id": source_id,
            "source_type": source_type,
            "entities": entities,
            "relations": relations,
        },
        config=_make_config(user_id),
    )


@mcp.tool
async def get_hub_entities(user_id: str, limit: int = 10) -> list[dict]:
    """가장 많은 연결을 가진 허브 엔티티 목록을 반환한다.

    Args:
        user_id: Supabase 사용자 UUID
        limit: 최대 반환 결과 수 (기본 10)
    """
    from app.agents.tools.graph_tools import get_hub_entities as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"limit": limit}, config=_make_config(user_id))


@mcp.tool
async def get_ego_graph(user_id: str, entity_name: str, depth: int = 2) -> dict:
    """특정 엔티티를 중심으로 N-hop 서브그래프(노드+엣지)를 반환한다.

    Args:
        user_id: Supabase 사용자 UUID
        entity_name: 중심 엔티티 이름
        depth: 탐색 깊이 (기본 2)
    """
    from app.agents.tools.graph_tools import get_ego_graph as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"entity_name": entity_name, "depth": depth}, config=_make_config(user_id))


@mcp.tool
async def get_orphan_entities(user_id: str, limit: int = 20) -> list[dict]:
    """관계가 없는 고립 엔티티 목록을 반환한다.

    Args:
        user_id: Supabase 사용자 UUID
        limit: 최대 반환 결과 수 (기본 20)
    """
    from app.agents.tools.graph_tools import get_orphan_entities as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"limit": limit}, config=_make_config(user_id))


@mcp.tool
async def suggest_connections(user_id: str, limit: int = 5) -> list[dict]:
    """AI 기반으로 잠재적 지식 연결을 제안한다.

    Args:
        user_id: Supabase 사용자 UUID
        limit: 최대 제안 수 (기본 5)
    """
    from app.agents.tools.graph_tools import suggest_connections as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"limit": limit}, config=_make_config(user_id))


# ===========================================================================
# 8. 회고 (Reflection) 도구
# ===========================================================================


@mcp.tool
async def generate_reflection_questions(user_id: str, content: str) -> list[str]:
    """일기 또는 대화 내용을 바탕으로 소크라테스식 회고 질문 3개를 생성한다.

    Args:
        user_id: 인증 검증용 UUID
        content: 질문을 생성할 일기 또는 대화 내용
    """
    from app.agents.tools.reflection_tools import generate_reflection_questions as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"content": content}, config=_make_config(user_id))


@mcp.tool
async def detect_cognitive_distortions(user_id: str, text: str) -> dict:
    """텍스트에서 CBT 기반 인지 왜곡 패턴을 감지한다.

    Args:
        user_id: 인증 검증용 UUID
        text: 분석할 사용자 텍스트
    """
    from app.agents.tools.reflection_tools import detect_cognitive_distortions as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"text": text}, config=_make_config(user_id))


@mcp.tool
async def generate_diary_draft(user_id: str, conversation_summary: str) -> str:
    """대화 요약을 바탕으로 일기 초안을 생성한다.

    Args:
        user_id: 인증 검증용 UUID
        conversation_summary: 소크라테스 대화 내용 요약
    """
    from app.agents.tools.reflection_tools import generate_diary_draft as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"conversation_summary": conversation_summary}, config=_make_config(user_id))


# ===========================================================================
# 9. 세션 (Session) 도구
# ===========================================================================


@mcp.tool
async def search_past_conversations(user_id: str, query: str, limit: int = 3) -> list[dict]:
    """과거 소크라테스 대화 세션을 토픽 태그 기반으로 검색한다.

    Args:
        user_id: Supabase 사용자 UUID
        query: 검색 쿼리 (공백 구분 키워드를 태그로 분리하여 검색)
        limit: 최대 반환 세션 수 (기본 3)
    """
    from app.agents.tools.session_tools import search_past_conversations as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"query": query, "limit": limit}, config=_make_config(user_id))


@mcp.tool
async def get_user_profile(user_id: str) -> dict:
    """사용자 관심사와 자주 등장하는 토픽을 분석하여 프로필을 반환한다.

    Args:
        user_id: Supabase 사용자 UUID
    """
    from app.agents.tools.session_tools import get_user_profile as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({}, config=_make_config(user_id))


# ===========================================================================
# 10. 리포트 (Report) 도구
# ===========================================================================


@mcp.tool
async def generate_daily_digest(user_id: str, date: str | None = None) -> dict:
    """오늘의 활동 다이제스트와 AI 소크라테스 질문을 생성한다.

    Args:
        user_id: Supabase 사용자 UUID
        date: 조회 날짜 ("YYYY-MM-DD"). None이면 오늘
    """
    from app.agents.tools.report_tools import generate_daily_digest as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"date": date}, config=_make_config(user_id))


@mcp.tool
async def generate_daily_insights(user_id: str) -> list[dict]:
    """오늘의 패턴·행동 제안 인사이트를 생성한다.

    Args:
        user_id: Supabase 사용자 UUID
    """
    from app.agents.tools.report_tools import generate_daily_insights as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({}, config=_make_config(user_id))


@mcp.tool
async def generate_weekly_report(user_id: str, week_offset: int = 0) -> dict:
    """최근 7일 주간 리포트를 생성한다.

    Args:
        user_id: Supabase 사용자 UUID
        week_offset: 0이면 이번 주, -1이면 지난 주
    """
    from app.agents.tools.report_tools import generate_weekly_report as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"week_offset": week_offset}, config=_make_config(user_id))


@mcp.tool
async def generate_monthly_report(user_id: str, month_offset: int = 0) -> dict:
    """최근 30일 월간 리포트를 생성한다.

    Args:
        user_id: Supabase 사용자 UUID
        month_offset: 0이면 이번 달, -1이면 지난 달
    """
    from app.agents.tools.report_tools import generate_monthly_report as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"month_offset": month_offset}, config=_make_config(user_id))


# ===========================================================================
# 11. 위임 (Delegation) 도구
# ===========================================================================


@mcp.tool
async def delegate_to_librarian(user_id: str, query: str, context: str = "") -> str:
    """Librarian 에이전트에게 스크랩/그래프 검색 작업을 위임한다.

    Args:
        user_id: Supabase 사용자 UUID
        query: 검색 쿼리 문자열
        context: 추가 컨텍스트 (선택 사항)
    """
    from app.agents.tools.delegation_tools import delegate_to_librarian as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"query": query, "context": context}, config=_make_config(user_id))


@mcp.tool
async def delegate_to_analyst(user_id: str, query: str, context: str = "") -> str:
    """Analyst 에이전트에게 지식 분석 작업을 위임한다.

    Args:
        user_id: Supabase 사용자 UUID
        query: 분석 쿼리 또는 관심 키워드
        context: 추가 컨텍스트 (선택 사항)
    """
    from app.agents.tools.delegation_tools import delegate_to_analyst as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke({"query": query, "context": context}, config=_make_config(user_id))


@mcp.tool
async def delegate_to_curator(
    user_id: str,
    source_id: str,
    source_type: str,
    content: str,
) -> dict:
    """Curator 에이전트에게 콘텐츠 그래프 저장 작업을 위임한다.

    Args:
        user_id: Supabase 사용자 UUID
        source_id: 출처 스크랩 또는 다이어리 ID
        source_type: "scrap" 또는 "diary"
        content: 엔티티/관계를 추출할 텍스트 콘텐츠
    """
    from app.agents.tools.delegation_tools import delegate_to_curator as _tool

    _ = UUID(user_id)
    return await _tool.ainvoke(
        {"source_id": source_id, "source_type": source_type, "content": content},
        config=_make_config(user_id),
    )


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
    run_mcp_server()
