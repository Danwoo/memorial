import os
import sys

import pytest

# Ensure backend directory is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.insert(0, backend_dir)


@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv("CI") == "true", reason="CI 환경에서 외부 네트워크 호출 불가")
async def test_curator_url():
    """curator_node URL 처리 기본 테스트."""
    from app.agents.librarian.nodes.curator import curator_node

    test_url = "https://www.example.com"

    state = {
        "target_text": test_url,
        "target_memory_id": "00000000-0000-0000-0000-000000000000",
    }

    result = await curator_node(state)

    assert "classification" in result or "tags" in result or "summary" in result
