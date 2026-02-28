import logging

logger = logging.getLogger(__name__)


class AgentRegistry:
    """에이전트 등록소 — agent_type 문자열로 적절한 컴파일된 그래프를 반환.

    get_agent_container()를 통해 서비스 계층에서 agent_type 기반 그래프를 선택할 때 사용한다.
    """

    _agents: dict = {}

    @classmethod
    def register(cls, agent_type: str, graph) -> None:
        """에이전트 그래프를 agent_type 키로 등록."""
        cls._agents[agent_type] = graph
        logger.debug("에이전트 등록됨: %s", agent_type)

    @classmethod
    def get(cls, agent_type: str):
        """agent_type으로 등록된 그래프 반환. 없으면 oracle로 폴백."""
        if agent_type not in cls._agents:
            logger.warning("미등록 agent_type=%s, oracle로 폴백", agent_type)
            return cls._agents.get("oracle")
        return cls._agents[agent_type]

    @classmethod
    def available(cls) -> list[str]:
        """등록된 agent_type 목록 반환."""
        return list(cls._agents.keys())

    @classmethod
    def is_registered(cls, agent_type: str) -> bool:
        """agent_type이 등록되어 있는지 확인."""
        return agent_type in cls._agents
