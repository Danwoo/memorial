import asyncio
import logging

logger = logging.getLogger(__name__)


class _SearchMixin:
    """하이브리드 검색 및 GraphRAG 조회 mixin."""

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

    # ------------------------------------------------------------------
    # GraphRAG — 엔티티 이웃 + 스크랩 ID 조회
    # ------------------------------------------------------------------
    def _sync_get_entity_neighborhood(self, entity_names: list[str], user_id: str, hops: int = 2) -> list[dict]:
        """엔티티 목록에서 N-hop 이내 관련 엔티티-관계 목록 조회 (동기).

        1-hop: rel_type 포함, 2-hop: rel_type 없음 (KuzuDB 가변 경로 제약).
        """
        if not entity_names:
            return []
        conn = self._get_conn()
        result: list[dict] = []
        seen_pairs: set[tuple[str, str]] = set()

        for name in entity_names[:8]:
            # 1-hop: rel_type 포함
            q1 = """
            MATCH (start:Entity {name: $name})-[r:ENTITY_REL]->(related:Entity)
            WHERE EXISTS { MATCH (mem:Memory {user_id: $user_id})-[:MENTIONS]->(related) }
            RETURN DISTINCT related.name AS name, related.type AS entity_type,
                   r.rel_type AS rel_type, 1 AS hop
            LIMIT 10
            """
            rows = self._result_to_dicts(conn.execute(q1, {"name": name, "user_id": user_id}))
            for r in rows:
                pair = (name, r.get("name", ""))
                if pair not in seen_pairs and r.get("name"):
                    seen_pairs.add(pair)
                    result.append(r)

            if hops >= 2:
                # 2-hop: 1-hop 이웃에서 다시 1-hop
                hop1_names = [r["name"] for r in rows if r.get("name")]
                for h1 in hop1_names[:4]:
                    q2 = """
                    MATCH (start:Entity {name: $name})-[r:ENTITY_REL]->(related:Entity)
                    WHERE EXISTS { MATCH (mem:Memory {user_id: $user_id})-[:MENTIONS]->(related) }
                    RETURN DISTINCT related.name AS name, related.type AS entity_type,
                           r.rel_type AS rel_type, 2 AS hop
                    LIMIT 5
                    """
                    rows2 = self._result_to_dicts(conn.execute(q2, {"name": h1, "user_id": user_id}))
                    for r in rows2:
                        pair = (h1, r.get("name", ""))
                        if pair not in seen_pairs and r.get("name"):
                            seen_pairs.add(pair)
                            result.append(r)

        return result

    async def get_entity_neighborhood(self, entity_names: list[str], user_id: str, hops: int = 2) -> list[dict]:
        """엔티티 목록에서 N-hop 이내 관련 엔티티-관계 조회."""
        if not self.db or not entity_names:
            return []
        try:
            return await asyncio.to_thread(self._sync_get_entity_neighborhood, entity_names, user_id, hops)
        except Exception:
            logger.exception("엔티티 이웃 조회 실패: entities=%s", entity_names[:3])
            return []

    def _sync_get_scrap_ids_for_entities(self, entity_names: list[str], user_id: str, limit: int = 20) -> list[dict]:
        """엔티티 이름 목록으로 연결된 스크랩 ID 조회 (동기). 빈도순 정렬."""
        if not entity_names:
            return []
        conn = self._get_conn()
        id_counts: dict[str, int] = {}
        for name in entity_names[:15]:
            q = """
            MATCH (mem:Memory {user_id: $user_id})-[:MENTIONS]->(e:Entity {name: $name})
            RETURN DISTINCT mem.id AS scrap_id
            LIMIT 10
            """
            rows = self._result_to_dicts(conn.execute(q, {"user_id": user_id, "name": name}))
            for r in rows:
                sid = r.get("scrap_id", "")
                if sid:
                    id_counts[sid] = id_counts.get(sid, 0) + 1
        sorted_ids = sorted(id_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"scrap_id": sid, "graph_score": cnt} for sid, cnt in sorted_ids[:limit]]

    async def get_scrap_ids_for_entities(self, entity_names: list[str], user_id: str, limit: int = 20) -> list[dict]:
        """엔티티 이름 목록으로 연결된 스크랩 ID 조회. graph_score = 매칭 엔티티 수."""
        if not self.db or not entity_names:
            return []
        try:
            return await asyncio.to_thread(self._sync_get_scrap_ids_for_entities, entity_names, user_id, limit)
        except Exception:
            logger.exception("스크랩 ID 조회 실패: entities=%s", entity_names[:3])
            return []
