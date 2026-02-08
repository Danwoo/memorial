"""
Graph Service
Business logic for knowledge graph operations
"""
import hashlib
import logging
from typing import Any
from uuid import UUID

from app.repositories.graph_repository import GraphRepository
from app.repositories.memory_repository import MemoryRepository

logger = logging.getLogger(__name__)


def _generate_node_id(prefix: str, content: str) -> str:
    """Generate a consistent node ID from content via MD5 hash prefix."""
    return f"{prefix}_{hashlib.md5(content.encode()).hexdigest()[:8]}"


def _resolve_node_label(source_type: str) -> str:
    """Map source_type to a graph node label."""
    if source_type in ("WEB", "PDF"):
        return "Resource"
    if source_type == "CHAT":
        return "Chat"
    return "Memory"


def _add_memory_node(
    memory: dict,
    nodes: list[dict],
    links: list[dict],
    seen_nodes: set[str],
    concept_nodes: dict[str, str],
) -> None:
    """Create a memory node and its associated concept nodes."""
    memory_id = str(memory.get("id", ""))
    source_type = memory.get("source_type", "NOTE")
    title = memory.get("title", "Untitled")
    tags = memory.get("tags", []) or []
    content = memory.get("content", "")[:200]
    url = memory.get("url", "")
    created_at = memory.get("created_at", "")

    node_label = _resolve_node_label(source_type)

    if memory_id not in seen_nodes:
        nodes.append({
            "id": memory_id,
            "label": node_label,
            "name": title,
            "url": url,
            "properties": {
                "title": title,
                "summary": content,
                "tags": tags,
                "source_type": source_type,
                "created_at": created_at,
            },
        })
        seen_nodes.add(memory_id)

    for tag in tags:
        concept_id = _generate_node_id("concept", tag)

        if concept_id not in seen_nodes:
            nodes.append({
                "id": concept_id,
                "label": "Concept",
                "name": tag,
                "properties": {"name": tag},
            })
            seen_nodes.add(concept_id)
            concept_nodes[tag] = concept_id

        link_type = "DISCUSSES" if node_label == "Chat" else "MENTIONS"
        links.append({
            "source": memory_id,
            "target": concept_id,
            "type": link_type,
        })

    # Relate co-occurring concepts
    for i, tag_a in enumerate(tags):
        for tag_b in tags[i + 1 :]:
            if tag_a in concept_nodes and tag_b in concept_nodes:
                links.append({
                    "source": concept_nodes[tag_a],
                    "target": concept_nodes[tag_b],
                    "type": "RELATED_TO",
                })


def _add_cross_type_links(
    memories: list[dict],
    links: list[dict],
) -> None:
    """Link Resource and Chat nodes that share tags."""
    resources = [m for m in memories if m.get("source_type") in ("WEB", "PDF")]
    chats = [m for m in memories if m.get("source_type") == "CHAT"]

    for resource in resources[:20]:
        resource_tags = set(resource.get("tags", []) or [])
        resource_id = str(resource.get("id", ""))

        for chat in chats[:20]:
            chat_tags = set(chat.get("tags", []) or [])
            chat_id = str(chat.get("id", ""))

            if resource_tags & chat_tags:
                links.append({
                    "source": chat_id,
                    "target": resource_id,
                    "type": "REFERENCES",
                })


def _deduplicate_links(links: list[dict]) -> list[dict]:
    """Remove duplicate and reverse-duplicate links."""
    unique: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    for link in links:
        key = (link["source"], link["target"], link["type"])
        reverse_key = (link["target"], link["source"], link["type"])
        if key not in seen and reverse_key not in seen:
            unique.append(link)
            seen.add(key)

    return unique


def _get_demo_graph_data() -> dict[str, list[Any]]:
    """Return rich demo graph data showing Resource-Chat relationships."""
    return {
        "nodes": [
            {"id": "res1", "label": "Resource", "name": "Attention Is All You Need",
             "properties": {"title": "Attention Is All You Need", "tags": ["AI", "Transformer", "NLP"]}},
            {"id": "res2", "label": "Resource", "name": "BERT: Pre-training of Deep Bidirectional Transformers",
             "properties": {"title": "BERT Paper", "tags": ["AI", "NLP", "BERT"]}},
            {"id": "res3", "label": "Resource", "name": "React 18 New Features",
             "properties": {"title": "React 18 Features", "tags": ["React", "Frontend", "Web"]}},
            {"id": "chat1", "label": "Chat", "name": "AI \ud504\ub85c\uc81d\ud2b8 \ubc29\ud5a5 \ub17c\uc758",
             "properties": {"title": "AI Project Discussion", "tags": ["AI", "Project"]}},
            {"id": "chat2", "label": "Chat", "name": "\ud504\ub860\ud2b8\uc5d4\ub4dc \uae30\uc220 \uc120\ud0dd",
             "properties": {"title": "Frontend Tech Selection", "tags": ["React", "Frontend"]}},
            {"id": "concept_ai", "label": "Concept", "name": "AI",
             "properties": {"name": "AI"}},
            {"id": "concept_nlp", "label": "Concept", "name": "NLP",
             "properties": {"name": "NLP"}},
            {"id": "concept_react", "label": "Concept", "name": "React",
             "properties": {"name": "React"}},
            {"id": "concept_frontend", "label": "Concept", "name": "Frontend",
             "properties": {"name": "Frontend"}},
            {"id": "concept_transformer", "label": "Concept", "name": "Transformer",
             "properties": {"name": "Transformer"}},
            {"id": "mem1", "label": "Memory", "name": "Transformer \ud559\uc2b5 \ub178\ud2b8",
             "properties": {"title": "Transformer Study Notes", "tags": ["AI", "Transformer"]}},
            {"id": "mem2", "label": "Memory", "name": "React Hooks \uc815\ub9ac",
             "properties": {"title": "React Hooks Summary", "tags": ["React", "Frontend"]}},
        ],
        "links": [
            {"source": "res1", "target": "concept_ai", "type": "MENTIONS"},
            {"source": "res1", "target": "concept_transformer", "type": "MENTIONS"},
            {"source": "res1", "target": "concept_nlp", "type": "MENTIONS"},
            {"source": "res2", "target": "concept_ai", "type": "MENTIONS"},
            {"source": "res2", "target": "concept_nlp", "type": "MENTIONS"},
            {"source": "res3", "target": "concept_react", "type": "MENTIONS"},
            {"source": "res3", "target": "concept_frontend", "type": "MENTIONS"},
            {"source": "chat1", "target": "concept_ai", "type": "DISCUSSES"},
            {"source": "chat2", "target": "concept_react", "type": "DISCUSSES"},
            {"source": "chat2", "target": "concept_frontend", "type": "DISCUSSES"},
            {"source": "chat1", "target": "res1", "type": "REFERENCES"},
            {"source": "chat1", "target": "res2", "type": "REFERENCES"},
            {"source": "chat2", "target": "res3", "type": "REFERENCES"},
            {"source": "mem1", "target": "res1", "type": "REFERENCES"},
            {"source": "mem1", "target": "concept_transformer", "type": "MENTIONS"},
            {"source": "mem2", "target": "res3", "type": "REFERENCES"},
            {"source": "mem2", "target": "concept_react", "type": "MENTIONS"},
            {"source": "concept_ai", "target": "concept_nlp", "type": "RELATED_TO"},
            {"source": "concept_ai", "target": "concept_transformer", "type": "RELATED_TO"},
            {"source": "concept_react", "target": "concept_frontend", "type": "RELATED_TO"},
        ],
    }


class GraphService:
    """Service for knowledge graph business logic"""

    def __init__(self, graph_repo: GraphRepository, memory_repo: MemoryRepository | None = None):
        self.graph_repo = graph_repo
        self.memory_repo = memory_repo

    @property
    def is_available(self) -> bool:
        """Check if graph features are available."""
        return self.graph_repo.is_connected

    async def save_knowledge_graph(
        self,
        memory_id: str,
        entities: list[dict[str, Any]],
        relations: list[dict[str, Any]]
    ) -> bool:
        """
        Save extracted entities and relations to the knowledge graph.
        Called by Librarian agent after processing.
        """
        if not self.is_available:
            return False

        try:
            await self.graph_repo.save_entities(entities, memory_id)
            await self.graph_repo.save_relations(relations)
            return True
        except Exception:
            logger.exception("Error saving to graph")
            return False

    async def get_visualization_data(
        self,
        limit: int = 100
    ) -> dict[str, Any]:
        """
        Get graph data for D3 visualization.
        Returns nodes and links.
        """
        if not self.is_available:
            return {"nodes": [], "links": []}

        return await self.graph_repo.get_graph_data(limit)

    async def build_graph_from_memories(
        self,
        user_id: UUID,
        limit: int = 100,
    ) -> dict[str, list[Any]]:
        """Generate graph data dynamically from actual memories."""
        if not self.memory_repo:
            return _get_demo_graph_data()

        try:
            memories = await self.memory_repo.get_all(user_id=user_id)

            nodes: list[dict[str, Any]] = []
            links: list[dict[str, Any]] = []
            seen_nodes: set[str] = set()
            concept_nodes: dict[str, str] = {}

            for memory in memories[:limit]:
                _add_memory_node(memory, nodes, links, seen_nodes, concept_nodes)

            _add_cross_type_links(memories, links)

            unique_links = _deduplicate_links(links)

            if not nodes:
                return _get_demo_graph_data()

            return {"nodes": nodes, "links": unique_links}

        except Exception:
            logger.exception("Error generating graph from memories")
            return _get_demo_graph_data()
