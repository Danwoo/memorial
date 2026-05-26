from app.repositories.mindmap._base import _BaseRepo
from app.repositories.mindmap._centrality import _CentralityMixin
from app.repositories.mindmap._count import _CountMixin
from app.repositories.mindmap._ego import _EgoMixin
from app.repositories.mindmap._maintenance import _MaintenanceMixin
from app.repositories.mindmap._path import _PathMixin
from app.repositories.mindmap._search import _SearchMixin
from app.repositories.mindmap._storage import _StorageMixin
from app.repositories.mindmap._visualization import _VisualizationMixin


class MindmapRepository(
    _StorageMixin,
    _VisualizationMixin,
    _CountMixin,
    _EgoMixin,
    _CentralityMixin,
    _SearchMixin,
    _PathMixin,
    _MaintenanceMixin,
    _BaseRepo,
):
    """KuzuDB 마인드맵 리포지토리 — mixin으로 책임별 분할.

    _BaseRepo가 self.db, self._get_conn 등 인프라를 제공.
    각 mixin은 그 위에서 도메인 로직을 캡슐화.
    """
    pass
