import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_iso_datetime(iso_str: str) -> datetime:
    """ISO 8601 문자열을 datetime으로 파싱. 'Z' 접미사 처리 포함.

    Args:
        iso_str: ISO datetime 문자열 (예: "2024-01-15T10:30:00Z")

    Returns:
        타임존 인식 datetime 객체.

    Raises:
        ValueError: 파싱 실패 시.
    """
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))


def parse_llm_json_response(raw: str) -> dict:
    """LLM 응답에서 JSON 파싱. 마크다운 코드 펜스 자동 제거.

    Args:
        raw: LLM 원본 응답 텍스트.

    Returns:
        파싱된 dict.

    Raises:
        json.JSONDecodeError: JSON 파싱 실패 시.
    """
    content = raw.strip()

    if content.startswith("```"):
        parts = content.split("```")
        if len(parts) >= 2:
            content = parts[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

    return json.loads(content)
