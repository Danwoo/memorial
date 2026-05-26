import logging

import kuzu

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class _BaseRepo:
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
            # buffer_pool_size를 32MB로 제한 (EC2 t2.micro 1GB RAM, 스타트업 메모리 압박 대응)
            self.db = kuzu.Database(path, buffer_pool_size=32 * 1024 * 1024)
            self._ensure_schema()
            logger.info("KuzuDB initialized at %s", path)
        except Exception:
            logger.exception("Failed to initialize KuzuDB")
            self.db = None

    def _ensure_schema(self):
        """노드/관계 테이블 + FTS 인덱스 보장.

        KuzuDB 0.11에서 일반 B-tree secondary index는 미지원이지만 FTS는 지원한다.
        Entity.name에 FTS 인덱스를 두어 `search_entities_by_name`/엔티티 lookup이
        선형 스캔이 아닌 inverted index lookup으로 동작하게 한다.

        Memory.user_id 같은 일반 필터링은 PK로 끌어올리지 않는 한 KuzuDB에서
        가속할 수 없다 (single-column PK 제약). 운영 데이터 규모가 커지면
        그래프 multi-tenancy(user별 Memory 노드 분리)를 검토해야 한다.
        """
        conn = kuzu.Connection(self.db)
        ddl_statements = [
            "CREATE NODE TABLE IF NOT EXISTS Entity(name STRING, type STRING, PRIMARY KEY(name))",
            "CREATE NODE TABLE IF NOT EXISTS Memory(id STRING, user_id STRING, PRIMARY KEY(id))",
            "CREATE REL TABLE IF NOT EXISTS MENTIONS(FROM Memory TO Entity)",
            "CREATE REL TABLE IF NOT EXISTS ENTITY_REL(FROM Entity TO Entity, rel_type STRING)",
        ]
        for stmt in ddl_statements:
            conn.execute(stmt)

        # FTS extension + 인덱스 등록 (CREATE_FTS_INDEX는 idempotent하지 않으므로 예외 무시)
        try:
            conn.execute("INSTALL FTS")
            conn.execute("LOAD EXTENSION FTS")
            conn.execute("CALL CREATE_FTS_INDEX('Entity', 'idx_entity_name', ['name'])")
            logger.info("KuzuDB FTS index on Entity.name registered")
        except Exception as exc:
            # 이미 존재하는 경우 또는 extension 미지원 환경 — 운영상 graceful
            msg = str(exc).lower()
            if "already exists" in msg or "exists" in msg:
                pass
            else:
                logger.warning("FTS index 등록 실패 (graceful): %s", exc)

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
