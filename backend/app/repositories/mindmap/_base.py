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
