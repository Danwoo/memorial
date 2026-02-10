"""
Graph Repository
Data access layer for Neo4j knowledge graph
"""

import asyncio
import logging

from langchain_community.graphs import Neo4jGraph

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

# Allowed node labels (extend as new entity types are added)
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
    }
)

# Allowed relationship types
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
    }
)

MAX_GRAPH_QUERY_LIMIT = 1000
MAX_GRAPH_TRAVERSAL_DEPTH = 3
MAX_RELATED_CONTEXT_RESULTS = 15


def _validate_label(label: str) -> str:
    """Validate a Neo4j node label against the whitelist. Rejects unknown labels."""
    cleaned = label.replace(" ", "")
    if cleaned in ALLOWED_NODE_LABELS:
        return cleaned
    logger.warning("Rejected unknown node label: '%s'. Falling back to 'Concept'.", label)
    return "Concept"


def _validate_rel_type(rel_type: str) -> str:
    """Validate a Neo4j relationship type against the whitelist. Rejects unknown types."""
    cleaned = rel_type.upper().replace(" ", "_")
    if cleaned in ALLOWED_REL_TYPES:
        return cleaned
    logger.warning("Rejected unknown rel type: '%s'. Falling back to 'RELATED_TO'.", rel_type)
    return "RELATED_TO"


class GraphRepository:
    """Repository for Neo4j graph operations"""

    def __init__(self, graph: Neo4jGraph | None = None):
        """
        Initialize with optional Neo4j connection.
        If not provided, attempts to connect using settings.
        """
        if graph:
            self.graph = graph
        else:
            self._init_connection()

    def _init_connection(self):
        """Initialize Neo4j connection from settings."""
        settings = get_settings()

        if not settings.NEO4J_URI or not settings.NEO4J_PASSWORD:
            self.graph = None
            logger.warning("Neo4j not configured. Graph features disabled.")
            return

        try:
            self.graph = Neo4jGraph(
                url=settings.NEO4J_URI, username=settings.NEO4J_USER or "neo4j", password=settings.NEO4J_PASSWORD
            )
        except Exception:
            logger.exception("Failed to connect to Neo4j")
            self.graph = None

    @property
    def is_connected(self) -> bool:
        """Check if Neo4j is connected."""
        return self.graph is not None

    def _sync_save_entities(self, entities: list[dict], source_id: str, user_id: str | None = None) -> None:
        """Synchronous implementation of save_entities."""
        for entity in entities:
            label = _validate_label(entity.get("type", "Concept"))
            name = entity.get("name")
            if not name:
                continue

            query = f"MERGE (e:{label} {{name: $name}})"
            self.graph.query(query, {"name": name})

        # Link entities to source memory (with user_id for filtering)
        if user_id:
            self.graph.query(
                "MERGE (m:Memory {id: $id}) SET m.user_id = $user_id",
                {"id": str(source_id), "user_id": user_id},
            )
        else:
            self.graph.query("MERGE (m:Memory {id: $id})", {"id": str(source_id)})

        for entity in entities:
            name = entity.get("name")
            if not name:
                continue

            query = """
            MATCH (m:Memory {id: $id}), (e {name: $name})
            MERGE (m)-[:MENTIONS]->(e)
            """
            self.graph.query(query, {"id": str(source_id), "name": name})

    async def save_entities(self, entities: list[dict], source_id: str, user_id: str | None = None) -> None:
        """Save entities to Neo4j graph."""
        if not self.graph:
            return
        await asyncio.to_thread(self._sync_save_entities, entities, source_id, user_id)

    def _sync_save_relations(self, relations: list[dict]) -> None:
        """Synchronous implementation of save_relations."""
        for rel in relations:
            source = rel.get("source")
            target = rel.get("target")
            rel_type = _validate_rel_type(rel.get("type", "RELATED_TO"))

            if not source or not target:
                continue

            query = f"""
            MATCH (a {{name: $source}}), (b {{name: $target}})
            MERGE (a)-[:{rel_type}]->(b)
            """
            self.graph.query(query, {"source": source, "target": target})

    async def save_relations(self, relations: list[dict]) -> None:
        """Save relations to Neo4j graph."""
        if not self.graph:
            return
        await asyncio.to_thread(self._sync_save_relations, relations)

    def _sync_get_graph_data(self, limit: int, user_id: str | None = None) -> dict[str, list]:
        """Synchronous implementation of get_graph_data."""
        safe_limit = max(1, min(int(limit), MAX_GRAPH_QUERY_LIMIT))

        if user_id:
            # Filter entities connected to this user's Memory nodes
            query = f"""
            MATCH (mem:Memory {{user_id: $user_id}})-[:MENTIONS]->(e)
            WITH COLLECT(DISTINCT e) AS userEntities
            UNWIND userEntities AS n
            MATCH (n)-[r]->(m)
            WHERE m IN userEntities
            RETURN
                n.name AS source_name,
                labels(n)[0] AS source_label,
                m.name AS target_name,
                labels(m)[0] AS target_label,
                type(r) AS rel_type
            LIMIT {safe_limit}
            """
            results = self.graph.query(query, {"user_id": user_id})
        else:
            query = f"""
            MATCH (n)-[r]->(m)
            WHERE NOT n:Memory AND NOT m:Memory
            RETURN
                n.name AS source_name,
                labels(n)[0] AS source_label,
                m.name AS target_name,
                labels(m)[0] AS target_label,
                type(r) AS rel_type
            LIMIT {safe_limit}
            """
            results = self.graph.query(query)

        nodes: dict[str, dict] = {}
        links = []

        for record in results:
            source_name = record.get("source_name")
            source_label = record.get("source_label", "Unknown")
            if source_name and source_name not in nodes:
                nodes[source_name] = {
                    "id": source_name,
                    "label": source_label,
                    "group": source_label,
                    "name": source_name,
                    "val": 1,
                    "properties": {},
                }

            target_name = record.get("target_name")
            target_label = record.get("target_label", "Unknown")
            if target_name and target_name not in nodes:
                nodes[target_name] = {
                    "id": target_name,
                    "label": target_label,
                    "group": target_label,
                    "name": target_name,
                    "val": 1,
                    "properties": {},
                }

            if source_name and target_name:
                links.append(
                    {
                        "source": source_name,
                        "target": target_name,
                        "type": record.get("rel_type", "RELATED_TO"),
                    }
                )
                # Increment degree for node sizing
                nodes[source_name]["val"] += 1
                nodes[target_name]["val"] += 1

        # Also include orphan entities (connected to user's memories but no inter-entity relations)
        if user_id:
            orphan_query = """
            MATCH (mem:Memory {user_id: $user_id})-[:MENTIONS]->(e)
            WHERE NOT (e)-[]->() AND NOT ()-[]->(e)
            RETURN DISTINCT e.name AS name, labels(e)[0] AS label
            """
            orphan_results = self.graph.query(orphan_query, {"user_id": user_id})
            for record in orphan_results:
                name = record.get("name")
                label = record.get("label", "Unknown")
                if name and name not in nodes:
                    nodes[name] = {
                        "id": name,
                        "label": label,
                        "group": label,
                        "name": name,
                        "val": 1,
                        "properties": {},
                    }

        return {"nodes": list(nodes.values()), "links": links}

    def _sync_get_related_context(self, topic: str, depth: int) -> list[dict]:
        """Synchronous: find entities related to a topic within N hops."""
        safe_depth = max(1, min(depth, MAX_GRAPH_TRAVERSAL_DEPTH))
        query = f"""
        MATCH (start {{name: $topic}})
        MATCH path = (start)-[r*1..{safe_depth}]-(related)
        WHERE related.name IS NOT NULL AND related.name <> $topic
        RETURN DISTINCT
            related.name AS name,
            labels(related)[0] AS label,
            type(last(relationships(path))) AS rel_type,
            length(path) AS distance
        ORDER BY distance
        LIMIT {MAX_RELATED_CONTEXT_RESULTS}
        """
        return self.graph.query(query, {"topic": topic})

    async def get_related_context(self, topic: str, depth: int = 2) -> list[dict]:
        """Find entities related to a topic within N hops in the knowledge graph."""
        if not self.graph:
            return []
        try:
            return await asyncio.to_thread(self._sync_get_related_context, topic, depth)
        except Exception:
            logger.exception("Error fetching related context for '%s'", topic)
            return []

    def _sync_delete_memory_node(self, memory_id: str) -> None:
        """Delete a Memory node and its MENTIONS relationships from Neo4j."""
        self.graph.query(
            "MATCH (m:Memory {id: $id})-[r:MENTIONS]->() DELETE r, m",
            {"id": memory_id},
        )

    async def delete_memory_node(self, memory_id: str) -> None:
        """Delete a Memory node and its relationships from the graph."""
        if not self.graph:
            return
        try:
            await asyncio.to_thread(self._sync_delete_memory_node, memory_id)
        except Exception:
            logger.exception("Error deleting memory node '%s' from Neo4j", memory_id)

    async def get_graph_data(self, limit: int = 100, user_id: str | None = None) -> dict[str, list]:
        """
        Retrieve graph data for visualization.
        Returns nodes and links in D3 compatible format.
        Filters by user_id when provided.
        """
        if not self.graph:
            return {"nodes": [], "links": []}

        try:
            return await asyncio.to_thread(self._sync_get_graph_data, limit, user_id)
        except Exception:
            logger.exception("Error fetching graph data")
            return {"nodes": [], "links": []}
