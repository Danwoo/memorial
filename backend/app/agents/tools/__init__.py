# backend/app/agents/tools/__init__.py
"""Memoir AI 에이전트 tool registry."""

# ---------------------------------------------------------------------------
# 개별 tool 파일 import
# ---------------------------------------------------------------------------

from app.agents.tools.analysis_tools import (
    compare_content,
    find_connections,
    get_community_insights,
    get_content_timeline,
    get_entity_timeline,
)
from app.agents.tools.content_tools import (
    analyze_sentiment,
    classify_content,
    extract_tags,
    inline_edit,
    summarize_content,
)
from app.agents.tools.delegation_tools import (
    delegate_to_analyst,
    delegate_to_curator,
    delegate_to_librarian,
)
from app.agents.tools.diary_tools import (
    get_diary_detail,
    get_diary_statistics,
    get_emotion_trend,
    list_diary_dates,
    search_diaries,
)
from app.agents.tools.graph_tools import (
    extract_entities,
    extract_relations,
    find_path_between_entities,
    get_ego_graph,
    get_hub_entities,
    get_orphan_entities,
    save_to_graph,
    suggest_connections,
)
from app.agents.tools.kb_tools import (
    get_scrap_detail,
    list_recent_scraps,
    list_scraps_by_tag,
    update_scrap_metadata,
)
from app.agents.tools.reflection_tools import (
    detect_cognitive_distortions,
    generate_diary_draft,
    generate_reflection_questions,
)
from app.agents.tools.report_tools import (
    generate_daily_digest,
    generate_daily_insights,
    generate_monthly_report,
    generate_weekly_report,
)
from app.agents.tools.retrieval_tools import (
    get_graph_context,
    search_graph_entities,
    search_scraps,
)
from app.agents.tools.session_tools import (
    get_user_profile,
    search_past_conversations,
)
from app.agents.tools.stats_tools import (
    get_activity_streak,
    get_knowledge_stats,
    get_topic_distribution,
)

# ---------------------------------------------------------------------------
# 에이전트별 tool 세트
# ---------------------------------------------------------------------------

SOCRATES_TOOLS = [
    search_diaries,
    get_diary_detail,
    get_emotion_trend,
    search_past_conversations,
    generate_reflection_questions,
    detect_cognitive_distortions,
    generate_diary_draft,
    delegate_to_librarian,
    delegate_to_analyst,
]

LIBRARIAN_TOOLS = [
    search_scraps,
    search_graph_entities,
    get_graph_context,
    search_diaries,
    get_community_insights,
    search_past_conversations,
    get_scrap_detail,
    list_recent_scraps,
    list_scraps_by_tag,
    delegate_to_curator,
    delegate_to_analyst,
]

ANALYST_TOOLS = [
    search_graph_entities,
    get_graph_context,
    get_community_insights,
    find_connections,
    find_path_between_entities,
    get_emotion_trend,
    search_scraps,
    get_ego_graph,
    get_hub_entities,
    get_entity_timeline,
    get_topic_distribution,
    get_content_timeline,
    compare_content,
    list_scraps_by_tag,
    get_knowledge_stats,
    delegate_to_librarian,
]

SCRIBE_TOOLS = [
    classify_content,
    summarize_content,
    extract_tags,
    analyze_sentiment,
    inline_edit,
    update_scrap_metadata,
    delegate_to_curator,
]

CURATOR_TOOLS = [
    extract_entities,
    extract_relations,
    save_to_graph,
    search_graph_entities,
    get_ego_graph,
    get_orphan_entities,
    get_hub_entities,
    suggest_connections,
    update_scrap_metadata,
]

REPORTER_TOOLS = [
    generate_daily_digest,
    generate_daily_insights,
    generate_weekly_report,
    generate_monthly_report,
    get_knowledge_stats,
    get_activity_streak,
    get_diary_statistics,
    list_recent_scraps,
    delegate_to_analyst,
    delegate_to_librarian,
]

# ---------------------------------------------------------------------------
# 전체 tool 합집합 (중복 제거 — 함수 객체 id 기준)
# ---------------------------------------------------------------------------

ALL_TOOLS = list(
    {
        id(t): t
        for t in (SOCRATES_TOOLS + LIBRARIAN_TOOLS + ANALYST_TOOLS + SCRIBE_TOOLS + CURATOR_TOOLS + REPORTER_TOOLS)
    }.values()
)

__all__ = [
    "ALL_TOOLS",
    "ANALYST_TOOLS",
    "CURATOR_TOOLS",
    "LIBRARIAN_TOOLS",
    "REPORTER_TOOLS",
    "SCRIBE_TOOLS",
    # agent tool sets
    "SOCRATES_TOOLS",
    # content_tools
    "analyze_sentiment",
    "classify_content",
    # analysis_tools
    "compare_content",
    # delegation_tools
    "delegate_to_analyst",
    "delegate_to_curator",
    "delegate_to_librarian",
    # reflection_tools
    "detect_cognitive_distortions",
    # graph_tools
    "extract_entities",
    "extract_relations",
    "extract_tags",
    "find_connections",
    "find_path_between_entities",
    # report_tools
    "generate_daily_digest",
    "generate_daily_insights",
    "generate_diary_draft",
    "generate_monthly_report",
    "generate_reflection_questions",
    "generate_weekly_report",
    # stats_tools
    "get_activity_streak",
    "get_community_insights",
    "get_content_timeline",
    # diary_tools
    "get_diary_detail",
    "get_diary_statistics",
    "get_ego_graph",
    "get_emotion_trend",
    "get_entity_timeline",
    # retrieval_tools
    "get_graph_context",
    "get_hub_entities",
    "get_knowledge_stats",
    "get_orphan_entities",
    # kb_tools
    "get_scrap_detail",
    "get_topic_distribution",
    # session_tools
    "get_user_profile",
    "inline_edit",
    "list_diary_dates",
    "list_recent_scraps",
    "list_scraps_by_tag",
    "save_to_graph",
    "search_diaries",
    "search_graph_entities",
    "search_past_conversations",
    "search_scraps",
    "suggest_connections",
    "summarize_content",
    "update_scrap_metadata",
]
