import logging

logger = logging.getLogger(__name__)

# 허용된 노드 라벨 화이트리스트
ALLOWED_NODE_LABELS = frozenset(
    {
        "Concept",
        "Person",
        "Organization",
        "Location",
        "Event",
        "Technology",
        "Product",
        "Memory",
        "Topic",
        "Idea",
        "Company",
        "Platform",
        "Framework",
        "Language",
        "Tool",
        "Project",
    }
)

# 허용된 관계 타입 화이트리스트
ALLOWED_REL_TYPES = frozenset(
    {
        "RELATED_TO",
        "MENTIONS",
        "PART_OF",
        "CAUSED_BY",
        "DEPENDS_ON",
        "SIMILAR_TO",
        "OPPOSITE_OF",
        "DERIVED_FROM",
        "USED_BY",
        "CREATED_BY",
        "WORKS_AT",
        "LOCATED_IN",
        "BELONGS_TO",
        "HAS",
        "IS_A",
        "USES",
        "USED_FOR",
        "BUILT_WITH",
        "INSPIRED_BY",
        "CONTAINS",
        "SUPPORTS",
        "CONTRADICTS",
        "LEADS_TO",
    }
)

MAX_GRAPH_QUERY_LIMIT = 1000
MAX_GRAPH_TRAVERSAL_DEPTH = 3
MAX_RELATED_CONTEXT_RESULTS = 15


def _validate_label(label: str) -> str:
    """노드 라벨을 화이트리스트에서 검증. 미등록 라벨은 'Concept'으로 폴백."""
    cleaned = label.replace(" ", "")
    if cleaned in ALLOWED_NODE_LABELS:
        return cleaned
    logger.warning("Rejected unknown node label: '%s'. Falling back to 'Concept'.", label)
    return "Concept"


def _validate_rel_type(rel_type: str) -> str:
    """관계 타입을 화이트리스트에서 검증. 미등록 타입은 'RELATED_TO'로 폴백."""
    cleaned = rel_type.upper().replace(" ", "_")
    if cleaned in ALLOWED_REL_TYPES:
        return cleaned
    logger.warning("Rejected unknown rel type: '%s'. Falling back to 'RELATED_TO'.", rel_type)
    return "RELATED_TO"
