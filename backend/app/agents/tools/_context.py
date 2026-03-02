# backend/app/agents/tools/_context.py
"""Tool 실행 시 RunnableConfig에서 user_id를 추출하는 유틸리티."""

from langchain_core.runnables import RunnableConfig


def get_user_id(config: RunnableConfig) -> str:
    """RunnableConfig의 configurable에서 user_id를 추출한다."""
    user_id = (config.get("configurable") or {}).get("user_id")
    if not user_id:
        raise ValueError("user_id가 config.configurable에 없습니다.")
    return user_id
