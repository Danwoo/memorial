import json
import logging
from datetime import datetime

from app.exceptions import LLMParseError

logger = logging.getLogger(__name__)


def parse_iso_datetime(iso_str: str) -> datetime:
    """ISO 8601 문자열을 datetime으로 파싱. 'Z' 접미사 처리 포함."""
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))


def parse_llm_json_response(raw: str) -> dict:
    """LLM 응답에서 JSON 파싱. 마크다운 코드 펜스 자동 제거.

    Raises:
        LLMParseError: JSON 파싱 실패 (모델이 spec과 다른 형식으로 응답한 경우).
    """
    content = raw.strip()

    if content.startswith("```"):
        parts = content.split("```")
        if len(parts) >= 2:
            content = parts[1]
            content = content.removeprefix("json")
        content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise LLMParseError(f"LLM JSON 응답 파싱 실패: {e}") from e
