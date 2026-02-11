"""
Graph Repository
Data access layer for KuzuDB knowledge graph
"""

import asyncio
import logging

import kuzu

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
    """Validate a node label against the whitelist. Rejects unknown labels."""
    cleaned = label.replace(" ", "")
    if cleaned in ALLOWED_NODE_LABELS:
        return cleaned
    logger.warning("Rejected unknown node label: '%s'. Falling back to 'Concept'.", label)
    return "Concept"


def _validate_rel_type(rel_type: str) -> str:
    """Validate a relationship type against the whitelist. Rejects unknown types."""
    cleaned = rel_type.upper().replace(" ", "_")
    if cleaned in ALLOWED_REL_TYPES:
        return cleaned
    logger.warning("Rejected unknown rel type: '%s'. Falling back to 'RELATED_TO'.", rel_type)
    return "RELATED_TO"


class GraphRepository:
    """Repository for KuzuDB graph operations"""

    def __init__(self, db_path: str | None = None):
        """
        Initialize with optional database path.
        If not provided, reads from settings.
        """
        self.db: kuzu.Database | None = None
        if db_path:
            self._init_db(db_path)
        else:
            self._init_connection()

    def _init_connection(self):
        """Initialize KuzuDB from settings."""
        settings = get_settings()
        db_path = settings.KUZU_DB_PATH
        if not db_path:
            logger.warning("KuzuDB not configured. Graph features disabled.")
            return
        self._init_db(db_path)

    def _init_db(self, path: str):
        """Open (or create) the KuzuDB database and ensure schema exists."""
        try:
            self.db = kuzu.Database(path)
            self._ensure_schema()
            logger.info("KuzuDB initialized at %s", path)
        except Exception:
            logger.exception("Failed to initialize KuzuDB")
            self.db = None

    def _ensure_schema(self):
        """Create node/rel tables if they don't already exist."""
        conn = kuzu.Connection(self.db)
        ddl_statements = [
            "CREATE NODE TABLE IF NOT EXISTS Entity(name STRING, type STRING, PRIMARY KEY(name))",
            "CREATE NODE TABLE IF NOT EXISTS Memory(id STRING, user_id STRING, PRIMARY KEY(id))",
            "CREATE REL TABLE IF NOT EXISTS MENTIONS(FROM Memory TO Entity)",
            "CREATE REL TABLE IF NOT EXISTS ENTITY_REL(FROM Entity TO Entity, rel_type STRING)",
        ]
        for stmt in ddl_statements:
            conn.execute(stmt)

    @property
    def is_connected(self) -> bool:
        """Check if KuzuDB is connected."""
        return self.db is not None

    def _get_conn(self) -> kuzu.Connection:
        """Create a new Connection (not thread-safe, so one per sync call)."""
        return kuzu.Connection(self.db)

    @staticmethod
    def _result_to_dicts(result) -> list[dict]:
        """Convert a KuzuDB QueryResult into a list of dicts."""
        if result is None:
            return []
        columns = result.get_column_names()
        rows = []
        while result.has_next():
            values = result.get_next()
            rows.append(dict(zip(columns, values, strict=False)))
        return rows

    # ------------------------------------------------------------------
    # Save entities
    # ------------------------------------------------------------------
    def _sync_save_entities(self, entities: list[dict], source_id: str, user_id: str | None = None) -> None:
        """Synchronous implementation of save_entities."""
        conn = self._get_conn()

        for entity in entities:
            label = _validate_label(entity.get("type", "Concept"))
            name = entity.get("name")
            if not name:
                continue
            conn.execute(
                "MERGE (e:Entity {name: $name}) SET e.type = $type",
                {"name": name, "type": label},
            )

        # Link entities to source memory (with user_id for filtering)
        if user_id:
            conn.execute(
                "MERGE (m:Memory {id: $id}) SET m.user_id = $user_id",
                {"id": str(source_id), "user_id": user_id},
            )
        else:
            conn.execute("MERGE (m:Memory {id: $id})", {"id": str(source_id)})

        for entity in entities:
            name = entity.get("name")
            if not name:
                continue
            conn.execute(
                """
                MATCH (m:Memory {id: $id}), (e:Entity {name: $name})
                WHERE NOT EXISTS { MATCH (m)-[:MENTIONS]->(e) }
                CREATE (m)-[:MENTIONS]->(e)
                """,
                {"id": str(source_id), "name": name},
            )

    async def save_entities(self, entities: list[dict], source_id: str, user_id: str | None = None) -> None:
        """Save entities to the knowledge graph."""
        if not self.db:
            return
        await asyncio.to_thread(self._sync_save_entities, entities, source_id, user_id)

    # ------------------------------------------------------------------
    # Save relations
    # ------------------------------------------------------------------
    def _sync_save_relations(self, relations: list[dict]) -> None:
        """Synchronous implementation of save_relations."""
        conn = self._get_conn()
        for rel in relations:
            source = rel.get("source")
            target = rel.get("target")
            rel_type = _validate_rel_type(rel.get("type", "RELATED_TO"))

            if not source or not target:
                continue

            conn.execute(
                """
                MATCH (a:Entity {name: $source}), (b:Entity {name: $target})
                WHERE NOT EXISTS {
                    MATCH (a)-[r:ENTITY_REL]->(b)
                    WHERE r.rel_type = $rel_type
                }
                CREATE (a)-[:ENTITY_REL {rel_type: $rel_type}]->(b)
                """,
                {"source": source, "target": target, "rel_type": rel_type},
            )

    async def save_relations(self, relations: list[dict]) -> None:
        """Save relations to the knowledge graph."""
        if not self.db:
            return
        await asyncio.to_thread(self._sync_save_relations, relations)

    # ------------------------------------------------------------------
    # Get graph data (for visualization)
    # ------------------------------------------------------------------
    def _sync_get_graph_data(self, limit: int, user_id: str | None = None) -> dict[str, list]:
        """Synchronous implementation of get_graph_data."""
        conn = self._get_conn()
        safe_limit = max(1, min(int(limit), MAX_GRAPH_QUERY_LIMIT))

        if user_id:
            # Entities connected to this user's memories, with inter-entity relations
            query = f"""
            MATCH (mem:Memory {{user_id: $user_id}})-[:MENTIONS]->(n:Entity)-[r:ENTITY_REL]->(m:Entity)<-[:MENTIONS]-(mem2:Memory {{user_id: $user_id}})
            RETURN DISTINCT
                n.name AS source_name,
                n.type AS source_label,
                m.name AS target_name,
                m.type AS target_label,
                r.rel_type AS rel_type
            LIMIT {safe_limit}
            """
            results = self._result_to_dicts(conn.execute(query, {"user_id": user_id}))
        else:
            query = f"""
            MATCH (n:Entity)-[r:ENTITY_REL]->(m:Entity)
            RETURN
                n.name AS source_name,
                n.type AS source_label,
                m.name AS target_name,
                m.type AS target_label,
                r.rel_type AS rel_type
            LIMIT {safe_limit}
            """
            results = self._result_to_dicts(conn.execute(query))

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
            MATCH (mem:Memory {user_id: $user_id})-[:MENTIONS]->(e:Entity)
            WHERE NOT EXISTS { MATCH (e)-[:ENTITY_REL]->(:Entity) }
              AND NOT EXISTS { MATCH (:Entity)-[:ENTITY_REL]->(e) }
            RETURN DISTINCT e.name AS name, e.type AS label
            """
            orphan_results = self._result_to_dicts(conn.execute(orphan_query, {"user_id": user_id}))
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

    # ------------------------------------------------------------------
    # Get related context (for Socrates chat)
    # ------------------------------------------------------------------
    def _sync_get_related_context(self, topic: str, depth: int) -> list[dict]:
        """Synchronous: find entities related to a topic within N hops."""
        conn = self._get_conn()
        safe_depth = max(1, min(depth, MAX_GRAPH_TRAVERSAL_DEPTH))
        query = f"""
        MATCH p = (start:Entity {{name: $topic}})-[:ENTITY_REL*1..{safe_depth}]-(related:Entity)
        WHERE related.name IS NOT NULL AND related.name <> $topic
        RETURN DISTINCT
            related.name AS name,
            related.type AS label,
            'RELATED_TO' AS rel_type,
            length(p) AS distance
        ORDER BY distance
        LIMIT {MAX_RELATED_CONTEXT_RESULTS}
        """
        return self._result_to_dicts(conn.execute(query, {"topic": topic}))

    async def get_related_context(self, topic: str, depth: int = 2) -> list[dict]:
        """Find entities related to a topic within N hops in the knowledge graph."""
        if not self.db:
            return []
        try:
            return await asyncio.to_thread(self._sync_get_related_context, topic, depth)
        except Exception:
            logger.exception("Error fetching related context for '%s'", topic)
            return []

    # ------------------------------------------------------------------
    # Delete memory node
    # ------------------------------------------------------------------
    def _sync_delete_memory_node(self, memory_id: str) -> None:
        """Delete a Memory node and all its relationships from the graph."""
        conn = self._get_conn()
        conn.execute(
            "MATCH (m:Memory {id: $id}) DETACH DELETE m",
            {"id": memory_id},
        )

    async def delete_memory_node(self, memory_id: str) -> None:
        """Delete a Memory node and its relationships from the graph."""
        if not self.db:
            return
        try:
            await asyncio.to_thread(self._sync_delete_memory_node, memory_id)
        except Exception:
            logger.exception("Error deleting memory node '%s' from graph", memory_id)

    async def get_graph_data(self, limit: int = 100, user_id: str | None = None) -> dict[str, list]:
        """
        Retrieve graph data for visualization.
        Returns nodes and links in D3 compatible format.
        Filters by user_id when provided.
        """
        if not self.db:
            return {"nodes": [], "links": []}

        try:
            return await asyncio.to_thread(self._sync_get_graph_data, limit, user_id)
        except Exception:
            logger.exception("Error fetching graph data")
            return {"nodes": [], "links": []}
