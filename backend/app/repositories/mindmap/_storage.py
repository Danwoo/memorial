import asyncio
import logging

from app.repositories.mindmap._constants import _validate_label, _validate_rel_type

logger = logging.getLogger(__name__)


class _StorageMixin:
    """엔티티/관계 저장 책임을 분리한 mixin."""

    # ------------------------------------------------------------------
    # 엔티티 저장 (배치 UNWIND — 1개씩 INSERT 대비 N배 성능)
    # ------------------------------------------------------------------
    def _sync_save_entities(self, entities: list[dict], source_id: str, user_id: str | None = None) -> None:
        """엔티티 저장 — UNWIND 배치로 단일 쿼리 실행."""
        conn = self._get_conn()

        # 유효한 엔티티만 normalize (label 화이트리스트 적용)
        normalized = [
            {"name": e["name"], "type": _validate_label(e.get("type", "Concept"))}
            for e in entities
            if e.get("name")
        ]
        if not normalized:
            return

        # 1) 엔티티 일괄 MERGE (단일 Cypher, 단일 plan 컴파일)
        conn.execute(
            """
            UNWIND $entities AS e
            MERGE (n:Entity {name: e.name})
            SET n.type = e.type
            """,
            {"entities": normalized},
        )

        # 2) Memory 노드 보장
        if user_id:
            conn.execute(
                "MERGE (m:Memory {id: $id}) SET m.user_id = $user_id",
                {"id": str(source_id), "user_id": user_id},
            )
        else:
            conn.execute("MERGE (m:Memory {id: $id})", {"id": str(source_id)})

        # 3) MENTIONS 관계 일괄 생성 (중복은 NOT EXISTS로 회피)
        conn.execute(
            """
            UNWIND $names AS n
            MATCH (m:Memory {id: $id}), (e:Entity {name: n})
            WHERE NOT EXISTS { MATCH (m)-[:MENTIONS]->(e) }
            CREATE (m)-[:MENTIONS]->(e)
            """,
            {"id": str(source_id), "names": [e["name"] for e in normalized]},
        )

    async def save_entities(self, entities: list[dict], source_id: str, user_id: str | None = None) -> None:
        """엔티티를 Knowledge Graph에 저장 (배치)."""
        if not self.db:
            return
        await asyncio.to_thread(self._sync_save_entities, entities, source_id, user_id)

    # ------------------------------------------------------------------
    # 관계 저장 (배치 UNWIND)
    # ------------------------------------------------------------------
    def _sync_save_relations(self, relations: list[dict]) -> None:
        """관계 저장 — UNWIND 배치로 단일 쿼리 실행."""
        conn = self._get_conn()

        normalized = [
            {
                "source": r["source"],
                "target": r["target"],
                "rel_type": _validate_rel_type(r.get("type", "RELATED_TO")),
            }
            for r in relations
            if r.get("source") and r.get("target")
        ]
        if not normalized:
            return

        conn.execute(
            """
            UNWIND $relations AS rel
            MATCH (a:Entity {name: rel.source}), (b:Entity {name: rel.target})
            WHERE NOT EXISTS {
                MATCH (a)-[existing:ENTITY_REL]->(b)
                WHERE existing.rel_type = rel.rel_type
            }
            CREATE (a)-[:ENTITY_REL {rel_type: rel.rel_type}]->(b)
            """,
            {"relations": normalized},
        )

    async def save_relations(self, relations: list[dict]) -> None:
        """관계를 Knowledge Graph에 저장 (배치)."""
        if not self.db:
            return
        await asyncio.to_thread(self._sync_save_relations, relations)
