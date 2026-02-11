import asyncio
import logging

import kuzu

from app.config.settings import get_settings

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


class GraphRepository:
    """KuzuDB 그래프 데이터 접근 계층."""

    def __init__(self, db_path: str | None = None):
        """KuzuDB 초기화. db_path 미지정 시 설정에서 읽어옴."""
        self.db: kuzu.Database | None = None
        if db_path:
            self._init_db(db_path)
        else:
            self._init_connection()

    def _init_connection(self):
        """설정 파일 기반 KuzuDB 초기화."""
        settings = get_settings()
        db_path = settings.KUZU_DB_PATH
        if not db_path:
            logger.warning("KuzuDB not configured. Graph features disabled.")
            return
        self._init_db(db_path)

    def _init_db(self, path: str):
        """KuzuDB 데이터베이스를 열고(또는 생성) 스키마 보장."""
        try:
            self.db = kuzu.Database(path)
            self._ensure_schema()
            logger.info("KuzuDB initialized at %s", path)
        except Exception:
            logger.exception("Failed to initialize KuzuDB")
            self.db = None

    def _ensure_schema(self):
        """노드/관계 테이블이 없으면 생성."""
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
        """KuzuDB 연결 여부 확인."""
        return self.db is not None

    def _get_conn(self) -> kuzu.Connection:
        """새 Connection 생성 (스레드 안전하지 않으므로 호출마다 생성)."""
        return kuzu.Connection(self.db)

    @staticmethod
    def _result_to_dicts(result) -> list[dict]:
        """KuzuDB QueryResult를 dict 리스트로 변환."""
        if result is None:
            return []
        columns = result.get_column_names()
        rows = []
        while result.has_next():
            values = result.get_next()
            rows.append(dict(zip(columns, values, strict=False)))
        return rows

    # ------------------------------------------------------------------
    # 엔티티 저장
    # ------------------------------------------------------------------
    def _sync_save_entities(self, entities: list[dict], source_id: str, user_id: str | None = None) -> None:
        """엔티티 저장 동기 구현."""
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

        # 엔티티를 출처 Memory 노드에 연결 (user_id로 필터링용)
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
        """엔티티를 Knowledge Graph에 저장.

        Args:
            entities: 저장할 엔티티 목록 ({name, type} dict)
            source_id: 출처 Memory ID
            user_id: 소유 사용자 ID (필터링용)
        """
        if not self.db:
            return
        await asyncio.to_thread(self._sync_save_entities, entities, source_id, user_id)

    # ------------------------------------------------------------------
    # 관계 저장
    # ------------------------------------------------------------------
    def _sync_save_relations(self, relations: list[dict]) -> None:
        """관계 저장 동기 구현."""
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
        """관계를 Knowledge Graph에 저장.

        Args:
            relations: 관계 목록 ({source, target, type} dict)
        """
        if not self.db:
            return
        await asyncio.to_thread(self._sync_save_relations, relations)

    # ------------------------------------------------------------------
    # 그래프 데이터 조회 (시각화용)
    # ------------------------------------------------------------------
    def _sync_get_graph_data(self, limit: int, user_id: str | None = None) -> dict[str, list]:
        """그래프 데이터 조회 동기 구현."""
        conn = self._get_conn()
        safe_limit = max(1, min(int(limit), MAX_GRAPH_QUERY_LIMIT))

        if user_id:
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
                # 노드 크기 산정을 위한 degree 증가
                nodes[source_name]["val"] += 1
                nodes[target_name]["val"] += 1

        # 관계가 없는 고아 엔티티도 포함 (사용자 Memory에 연결된 것만)
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
    # 관련 컨텍스트 조회 (Socrates 챗용)
    # ------------------------------------------------------------------
    def _sync_get_related_context(self, topic: str, depth: int) -> list[dict]:
        """주제와 N-hop 내 연관 엔티티 탐색 동기 구현."""
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
        """Knowledge Graph에서 주제와 N-hop 이내 관련 엔티티 조회.

        Args:
            topic: 검색 주제 (엔티티 이름)
            depth: 탐색 깊이 (기본 2)
        """
        if not self.db:
            return []
        try:
            return await asyncio.to_thread(self._sync_get_related_context, topic, depth)
        except Exception:
            logger.exception("Error fetching related context for '%s'", topic)
            return []

    # ------------------------------------------------------------------
    # Memory 노드 삭제
    # ------------------------------------------------------------------
    def _sync_delete_memory_node(self, memory_id: str) -> None:
        """Memory 노드와 연결된 관계를 그래프에서 삭제."""
        conn = self._get_conn()
        conn.execute(
            "MATCH (m:Memory {id: $id}) DETACH DELETE m",
            {"id": memory_id},
        )

    async def delete_memory_node(self, memory_id: str) -> None:
        """Memory 노드와 관계를 그래프에서 삭제."""
        if not self.db:
            return
        try:
            await asyncio.to_thread(self._sync_delete_memory_node, memory_id)
        except Exception:
            logger.exception("Error deleting memory node '%s' from graph", memory_id)

    async def get_graph_data(self, limit: int = 100, user_id: str | None = None) -> dict[str, list]:
        """시각화용 그래프 데이터 조회. D3 호환 {nodes, links} 포맷 반환.

        Args:
            limit: 최대 결과 수 (기본 100)
            user_id: 사용자 ID (지정 시 해당 사용자 데이터만 필터링)
        """
        if not self.db:
            return {"nodes": [], "links": []}

        try:
            return await asyncio.to_thread(self._sync_get_graph_data, limit, user_id)
        except Exception:
            logger.exception("Error fetching graph data")
            return {"nodes": [], "links": []}
