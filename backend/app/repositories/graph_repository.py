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
ALLOWED_NODE_LABELS = frozenset({
    "Concept", "Person", "Organization", "Location", "Event",
    "Technology", "Product", "Memory", "Topic", "Idea",
    "Company", "Platform", "Framework", "Language", "Tool",
})

# Allowed relationship types
ALLOWED_REL_TYPES = frozenset({
    "RELATED_TO", "MENTIONS", "PART_OF", "CAUSED_BY", "DEPENDS_ON",
    "SIMILAR_TO", "OPPOSITE_OF", "DERIVED_FROM", "USED_BY", "CREATED_BY",
    "WORKS_AT", "LOCATED_IN", "BELONGS_TO", "HAS", "IS_A",
    "USES", "USED_FOR", "BUILT_WITH", "INSPIRED_BY", "CONTAINS",
})

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
                url=settings.NEO4J_URI,
                username=settings.NEO4J_USER or "neo4j",
                password=settings.NEO4J_PASSWORD
            )
        except Exception:
            logger.exception("Failed to connect to Neo4j")
            self.graph = None

    @property
    def is_connected(self) -> bool:
        """Check if Neo4j is connected."""
        return self.graph is not None

    def _sync_save_entities(self, entities: list[dict], source_id: str) -> None:
        """Synchronous implementation of save_entities."""
        for entity in entities:
            label = _validate_label(entity.get("type", "Concept"))
            name = entity.get("name")
            if not name:
                continue

            query = f"MERGE (e:{label} {{name: $name}})"
            self.graph.query(query, {"name": name})

        # Link entities to source memory
        self.graph.query(
            "MERGE (m:Memory {id: $id})",
            {"id": str(source_id)}
        )

        for entity in entities:
            name = entity.get("name")
            if not name:
                continue

            query = """
            MATCH (m:Memory {id: $id}), (e {name: $name})
            MERGE (m)-[:MENTIONS]->(e)
            """
            self.graph.query(query, {"id": str(source_id), "name": name})

    async def save_entities(
        self,
        entities: list[dict],
        source_id: str
    ) -> None:
        """Save entities to Neo4j graph."""
        if not self.graph:
            return
        await asyncio.to_thread(self._sync_save_entities, entities, source_id)

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

    async def save_relations(
        self,
        relations: list[dict]
    ) -> None:
        """Save relations to Neo4j graph."""
        if not self.graph:
            return
        await asyncio.to_thread(self._sync_save_relations, relations)

    def _sync_get_graph_data(self, limit: int) -> dict[str, list]:
        """Synchronous implementation of get_graph_data."""
        safe_limit = max(1, min(int(limit), MAX_GRAPH_QUERY_LIMIT))
        query = f"""
        MATCH (n)-[r]->(m)
        WHERE NOT n:Memory AND NOT m:Memory
        RETURN
            n.name as source_name,
            n.id as source_id,
            labels(n)[0] as source_label,
            m.name as target_name,
            m.id as target_id,
            labels(m)[0] as target_label,
            type(r) as rel_type
        LIMIT {safe_limit}
        """
        results = self.graph.query(query)

        nodes = {}
        links = []

        for record in results:
            source_id = record.get('source_id') or record.get('source_name')
            source_label = record.get('source_label', 'Unknown')
            if source_id and source_id not in nodes:
                nodes[source_id] = {
                    "id": source_id,
                    "label": source_label,
                    "group": source_label,
                    "name": record.get('source_name', source_id),
                }

            target_id = record.get('target_id') or record.get('target_name')
            target_label = record.get('target_label', 'Unknown')
            if target_id and target_id not in nodes:
                nodes[target_id] = {
                    "id": target_id,
                    "label": target_label,
                    "group": target_label,
                    "name": record.get('target_name', target_id),
                }

            if source_id and target_id:
                links.append({
                    "source": source_id,
                    "target": target_id,
                    "type": record.get('rel_type', 'RELATED_TO')
                })

        return {
            "nodes": list(nodes.values()),
            "links": links
        }

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

    async def get_graph_data(self, limit: int = 100) -> dict[str, list]:
        """
        Retrieve graph data for visualization.
        Returns nodes and links in D3 compatible format.
        """
        if not self.graph:
            return {"nodes": [], "links": []}

        try:
            return await asyncio.to_thread(self._sync_get_graph_data, limit)
        except Exception:
            logger.exception("Error fetching graph data")
            return {"nodes": [], "links": []}

