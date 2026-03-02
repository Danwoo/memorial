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


class MindmapRepository:
    """KuzuDB 마인드맵 데이터 접근 계층."""

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

        results = self._query_entity_relations(conn, safe_limit, user_id)
        nodes, links = self._build_graph_structures(results)

        # 관계가 없는 고아 엔티티도 포함 (사용자 Memory에 연결된 것만)
        if user_id:
            self._add_orphan_entities(conn, user_id, nodes)

        return {"nodes": list(nodes.values()), "links": links}

    def _query_entity_relations(
        self,
        conn: kuzu.Connection,
        limit: int,
        user_id: str | None,
    ) -> list[dict]:
        """엔티티 간 관계 쿼리 실행."""
        if user_id:
            query = f"""
            MATCH (mem:Memory {{user_id: $user_id}})-[:MENTIONS]->(n:Entity)-[r:ENTITY_REL]->(m:Entity)<-[:MENTIONS]-(mem2:Memory {{user_id: $user_id}})
            RETURN DISTINCT
                n.name AS source_name, n.type AS source_label,
                m.name AS target_name, m.type AS target_label,
                r.rel_type AS rel_type
            LIMIT {limit}
            """
            return self._result_to_dicts(conn.execute(query, {"user_id": user_id}))

        query = f"""
        MATCH (n:Entity)-[r:ENTITY_REL]->(m:Entity)
        RETURN
            n.name AS source_name, n.type AS source_label,
            m.name AS target_name, m.type AS target_label,
            r.rel_type AS rel_type
        LIMIT {limit}
        """
        return self._result_to_dicts(conn.execute(query))

    @staticmethod
    def _make_node(name: str, label: str) -> dict:
        """D3 호환 노드 dict 생성."""
        return {
            "id": name,
            "label": label,
            "group": label,
            "name": name,
            "val": 1,
            "properties": {},
        }

    def _build_graph_structures(
        self,
        results: list[dict],
    ) -> tuple[dict[str, dict], list[dict]]:
        """쿼리 결과에서 D3 호환 nodes/links 구조 생성."""
        nodes: dict[str, dict] = {}
        links: list[dict] = []

        for record in results:
            source_name = record.get("source_name")
            target_name = record.get("target_name")

            if source_name and source_name not in nodes:
                nodes[source_name] = self._make_node(source_name, record.get("source_label", "Unknown"))
            if target_name and target_name not in nodes:
                nodes[target_name] = self._make_node(target_name, record.get("target_label", "Unknown"))

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

        return nodes, links

    def _add_orphan_entities(
        self,
        conn: kuzu.Connection,
        user_id: str,
        nodes: dict[str, dict],
    ) -> None:
        """관계가 없는 고아 엔티티를 nodes에 추가."""
        orphan_query = """
        MATCH (mem:Memory {user_id: $user_id})-[:MENTIONS]->(e:Entity)
        WHERE NOT EXISTS { MATCH (e)-[:ENTITY_REL]->(:Entity) }
          AND NOT EXISTS { MATCH (:Entity)-[:ENTITY_REL]->(e) }
        RETURN DISTINCT e.name AS name, e.type AS label
        """
        for record in self._result_to_dicts(conn.execute(orphan_query, {"user_id": user_id})):
            name = record.get("name")
            if name and name not in nodes:
                nodes[name] = self._make_node(name, record.get("label", "Unknown"))

    # ------------------------------------------------------------------
    # 관련 컨텍스트 조회 (Socrates 챗용)
    # ------------------------------------------------------------------
    def _sync_get_related_context(self, topic: str, depth: int) -> list[dict]:
        """주제와 직접 연결된 엔티티 탐색 동기 구현 (depth=1, 실제 rel_type 반환)."""
        conn = self._get_conn()
        # depth=1 직접 쿼리로 엣지 속성(rel_type) 접근
        query = f"""
        MATCH (start:Entity {{name: $topic}})-[r:ENTITY_REL]->(related:Entity)
        WHERE related.name IS NOT NULL AND related.name <> $topic
        RETURN DISTINCT
            related.name AS name,
            related.type AS label,
            r.rel_type AS rel_type,
            1 AS distance
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
    # Ego Graph (N-hop 서브그래프) 조회
    # ------------------------------------------------------------------
    def _sync_get_ego_graph(self, node_name: str, depth: int, user_id: str) -> dict[str, list]:
        """중심 노드에서 N-hop 이내 서브그래프 조회 동기 구현."""
        conn = self._get_conn()
        safe_depth = max(1, min(depth, MAX_GRAPH_TRAVERSAL_DEPTH))

        # 중심 노드 존재 여부 확인 (해당 사용자의 Memory에 연결된 것만)
        center_check = """
        MATCH (mem:Memory {user_id: $user_id})-[:MENTIONS]->(center:Entity {name: $name})
        RETURN center.name AS name, center.type AS type
        LIMIT 1
        """
        center_rows = self._result_to_dicts(conn.execute(center_check, {"user_id": user_id, "name": node_name}))
        if not center_rows:
            return {"nodes": [], "links": []}

        center = center_rows[0]

        # N-hop 이내 연결된 엔티티 수집 (사용자 소유 엔티티만)
        neighbor_query = f"""
        MATCH (center:Entity {{name: $name}})-[:ENTITY_REL*1..{safe_depth}]-(neighbor:Entity)
        WHERE neighbor.name <> $name
          AND EXISTS {{ MATCH (mem:Memory {{user_id: $user_id}})-[:MENTIONS]->(neighbor) }}
        RETURN DISTINCT neighbor.name AS name, neighbor.type AS type
        """
        neighbor_rows = self._result_to_dicts(conn.execute(neighbor_query, {"name": node_name, "user_id": user_id}))

        # 중심 노드만 있고 연결 없는 경우 → 단일 노드 반환
        if not neighbor_rows:
            node = self._make_node(center["name"], center.get("type", "Unknown"))
            return {"nodes": [node], "links": []}

        # 서브그래프 내부 엔티티 간 모든 ENTITY_REL 링크 조회
        # KuzuDB는 IN 리스트 파라미터를 직접 지원하지 않으므로 개별 쿼리 조합
        internal_query = f"""
        MATCH (mem:Memory {{user_id: $user_id}})-[:MENTIONS]->(a:Entity)-[r:ENTITY_REL]->(b:Entity)<-[:MENTIONS]-(mem2:Memory {{user_id: $user_id}})
        WHERE a.name = $name OR EXISTS {{ MATCH (center:Entity {{name: $name}})-[:ENTITY_REL*1..{safe_depth}]-(a) }}
        WITH a, r, b
        WHERE (b.name = $name OR EXISTS {{ MATCH (center2:Entity {{name: $name}})-[:ENTITY_REL*1..{safe_depth}]-(b) }})
        RETURN DISTINCT
            a.name AS source_name, a.type AS source_label,
            b.name AS target_name, b.type AS target_label,
            r.rel_type AS rel_type
        """
        internal_rows = self._result_to_dicts(conn.execute(internal_query, {"name": node_name, "user_id": user_id}))

        # _build_graph_structures로 노드/링크 생성
        nodes, links = self._build_graph_structures(internal_rows)

        # 중심 노드가 링크에 없어도 반드시 포함
        if node_name not in nodes:
            nodes[node_name] = self._make_node(center["name"], center.get("type", "Unknown"))

        # 이웃 노드 중 링크에 포함되지 않은 것도 추가
        for row in neighbor_rows:
            name = row["name"]
            if name not in nodes:
                nodes[name] = self._make_node(name, row.get("type", "Unknown"))

        return {"nodes": list(nodes.values()), "links": links}

    async def get_ego_graph(self, node_name: str, depth: int = 1, user_id: str | None = None) -> dict[str, list]:
        """중심 노드 기준 N-hop Ego Graph 조회.

        Args:
            node_name: 중심 엔티티 이름
            depth: 탐색 깊이 (기본 1, 최대 MAX_GRAPH_TRAVERSAL_DEPTH)
            user_id: 사용자 ID (필수 — 미지정 시 빈 그래프 반환)
        """
        if not self.db or not user_id:
            return {"nodes": [], "links": []}
        safe_depth = max(1, min(depth, MAX_GRAPH_TRAVERSAL_DEPTH))
        try:
            return await asyncio.to_thread(self._sync_get_ego_graph, node_name, safe_depth, user_id)
        except Exception:
            logger.exception("Ego graph 조회 실패: node='%s'", node_name)
            return {"nodes": [], "links": []}

    def _sync_get_default_ego_node(self, user_id: str) -> str | None:
        """ENTITY_REL 연결 수가 가장 많은 엔티티 이름 반환 (동기)."""
        conn = self._get_conn()
        query = """
        MATCH (mem:Memory {user_id: $user_id})-[:MENTIONS]->(e:Entity)-[r:ENTITY_REL]-(:Entity)
        WITH e.name AS name, count(r) AS degree
        ORDER BY degree DESC
        LIMIT 1
        RETURN name
        """
        rows = self._result_to_dicts(conn.execute(query, {"user_id": user_id}))
        if rows:
            return rows[0].get("name")
        return None

    async def get_default_ego_node(self, user_id: str) -> str | None:
        """사용자의 가장 연결이 많은 엔티티 이름을 기본 Ego 중심 노드로 반환."""
        if not self.db:
            return None
        try:
            return await asyncio.to_thread(self._sync_get_default_ego_node, user_id)
        except Exception:
            logger.exception("기본 ego 노드 조회 실패: user_id='%s'", user_id)
            return None

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

    # ------------------------------------------------------------------
    # 인사이트 분석용 조회 메서드
    # ------------------------------------------------------------------
    def _sync_get_all_edges(self, user_id: str) -> list[dict]:
        """클러스터 분석용 전체 엔티티 관계 동기 조회."""
        conn = self._get_conn()
        query = """
        MATCH (mem:Memory {user_id: $user_id})-[:MENTIONS]->(a:Entity)-[r:ENTITY_REL]->(b:Entity)<-[:MENTIONS]-(mem2:Memory {user_id: $user_id})
        RETURN DISTINCT a.name AS source, a.type AS source_type, b.name AS target, b.type AS target_type, r.rel_type AS rel_type
        """
        return self._result_to_dicts(conn.execute(query, {"user_id": user_id}))

    async def get_all_edges(self, user_id: str) -> list[dict]:
        """클러스터 분석용 전체 엔티티 관계 조회."""
        if not self.db:
            return []
        try:
            return await asyncio.to_thread(self._sync_get_all_edges, user_id)
        except Exception:
            logger.exception("Error fetching all edges")
            return []

    def _sync_get_hub_nodes(self, user_id: str, top_n: int) -> list[dict]:
        """degree 기준 상위 N 노드 동기 조회."""
        conn = self._get_conn()
        query = f"""
        MATCH (mem:Memory {{user_id: $user_id}})-[:MENTIONS]->(e:Entity)-[r:ENTITY_REL]-(:Entity)
        WITH e.name AS name, e.type AS type, count(r) AS degree
        ORDER BY degree DESC
        LIMIT {max(1, min(top_n, 20))}
        RETURN name, type, degree
        """
        return self._result_to_dicts(conn.execute(query, {"user_id": user_id}))

    async def get_hub_nodes(self, user_id: str, top_n: int = 5) -> list[dict]:
        """degree 기준 상위 N 허브 노드 조회."""
        if not self.db:
            return []
        try:
            return await asyncio.to_thread(self._sync_get_hub_nodes, user_id, top_n)
        except Exception:
            logger.exception("Error fetching hub nodes")
            return []

    def _sync_get_orphan_entities(self, user_id: str) -> list[dict]:
        """관계 없는 고아 엔티티 동기 조회."""
        conn = self._get_conn()
        query = """
        MATCH (mem:Memory {user_id: $user_id})-[:MENTIONS]->(e:Entity)
        WHERE NOT EXISTS { MATCH (e)-[:ENTITY_REL]->(:Entity) }
          AND NOT EXISTS { MATCH (:Entity)-[:ENTITY_REL]->(e) }
        RETURN DISTINCT e.name AS name, e.type AS type
        """
        return self._result_to_dicts(conn.execute(query, {"user_id": user_id}))

    async def get_orphan_entities(self, user_id: str) -> list[dict]:
        """관계 없는 고아 엔티티 조회."""
        if not self.db:
            return []
        try:
            return await asyncio.to_thread(self._sync_get_orphan_entities, user_id)
        except Exception:
            logger.exception("Error fetching orphan entities")
            return []

    # ------------------------------------------------------------------
    # 하이브리드 검색용 그래프 검색 메서드
    # ------------------------------------------------------------------
    def _sync_search_entities_by_name(self, query: str, user_id: str) -> list[dict]:
        """엔티티 이름에 쿼리 키워드가 포함된 엔티티 검색 (동기)."""
        conn = self._get_conn()
        # 쿼리를 공백 기준으로 분리해서 각 키워드가 이름에 포함되는지 검사
        keywords = [kw.strip() for kw in query.split() if len(kw.strip()) >= 1]
        if not keywords:
            return []

        all_results: list[dict] = []
        for keyword in keywords[:5]:  # 최대 5개 키워드
            q = """
            MATCH (mem:Memory {user_id: $user_id})-[:MENTIONS]->(e:Entity)
            WHERE contains(lower(e.name), lower($keyword))
            RETURN DISTINCT e.name AS name, e.type AS type
            LIMIT 10
            """
            results = self._result_to_dicts(conn.execute(q, {"user_id": user_id, "keyword": keyword}))
            all_results.extend(results)

        # 중복 제거
        seen: set[str] = set()
        unique: list[dict] = []
        for r in all_results:
            name = r.get("name", "")
            if name and name not in seen:
                seen.add(name)
                unique.append(r)
        return unique

    async def search_entities_by_name(self, query: str, user_id: str) -> list[dict]:
        """엔티티 이름에 쿼리 키워드가 포함된 엔티티 검색."""
        if not self.db:
            return []
        try:
            return await asyncio.to_thread(self._sync_search_entities_by_name, query, user_id)
        except Exception:
            logger.exception("엔티티 이름 검색 실패: query='%s'", query)
            return []

    async def search_entities(
        self,
        keyword: str,
        user_id: str,
        entity_type: str = "",
        limit: int = 10,
    ) -> list[dict]:
        """키워드와 엔티티 타입으로 Knowledge Graph 엔티티를 검색한다.

        Args:
            keyword: 엔티티 이름 검색 키워드
            user_id: 사용자 ID (해당 사용자의 Memory에 연결된 엔티티만 반환)
            entity_type: 필터링할 엔티티 타입. 빈 문자열이면 전체 타입 반환
            limit: 최대 반환 결과 수

        Returns:
            name, type 필드를 가진 dict 리스트
        """
        results = await self.search_entities_by_name(keyword, user_id)

        if entity_type:
            normalized = entity_type.strip()
            results = [r for r in results if r.get("type", "") == normalized]

        return results[: max(1, limit)]

    def _sync_search_memories_by_entities(self, entity_names: list[str], user_id: str, limit: int) -> list[dict]:
        """엔티티 이름으로 연결된 메모리 ID 검색 (동기)."""
        conn = self._get_conn()
        if not entity_names:
            return []

        all_scrap_ids: list[dict] = []
        for name in entity_names[:10]:  # 최대 10개 엔티티
            q = f"""
            MATCH (mem:Memory {{user_id: $user_id}})-[:MENTIONS]->(e:Entity {{name: $name}})
            RETURN DISTINCT mem.id AS scrap_id
            LIMIT {max(1, min(limit, 20))}
            """
            results = self._result_to_dicts(conn.execute(q, {"user_id": user_id, "name": name}))
            all_scrap_ids.extend(results)

        # 중복 제거 및 빈도순 정렬 (많이 등장하는 스크랩이 더 관련성 높음)
        id_counts: dict[str, int] = {}
        for r in all_scrap_ids:
            mid = r.get("scrap_id", "")
            if mid:
                id_counts[mid] = id_counts.get(mid, 0) + 1

        sorted_ids = sorted(id_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"scrap_id": mid, "graph_score": count} for mid, count in sorted_ids[:limit]]

    async def search_memories_by_entities(self, entity_names: list[str], user_id: str, limit: int = 10) -> list[dict]:
        """엔티티 이름으로 연결된 메모리 ID 검색. graph_score는 매칭된 엔티티 수."""
        if not self.db:
            return []
        try:
            return await asyncio.to_thread(self._sync_search_memories_by_entities, entity_names, user_id, limit)
        except Exception:
            logger.exception("엔티티 기반 메모리 검색 실패")
            return []

    async def search_memories_via_graph(self, query: str, user_id: str, limit: int = 10) -> list[dict]:
        """쿼리 → 엔티티 이름 매칭 → MENTIONS 엣지 → 메모리 ID 반환.

        그래프 기반 검색 파이프라인:
        1. 쿼리 키워드로 엔티티 이름 CONTAINS 매칭
        2. 매칭된 엔티티의 관련 엔티티 1-hop 탐색
        3. 모든 엔티티에서 MENTIONS 역방향 탐색으로 메모리 ID 수집
        """
        if not self.db:
            return []

        try:
            # 1단계: 키워드로 엔티티 검색
            matched_entities = await self.search_entities_by_name(query, user_id)
            entity_names = [e["name"] for e in matched_entities]

            if not entity_names:
                return []

            # 2단계: 1-hop 관련 엔티티 추가
            expanded_names = set(entity_names)
            for name in entity_names[:3]:  # 상위 3개만 확장
                related = await self.get_related_context(name, depth=1)
                for r in related[:3]:
                    expanded_names.add(r.get("name", ""))

            # 3단계: 엔티티 → 메모리 매핑
            return await self.search_memories_by_entities(list(expanded_names), user_id, limit)
        except Exception:
            logger.exception("그래프 기반 메모리 검색 실패: query='%s'", query)
            return []

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
