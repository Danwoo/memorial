import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_iso_datetime(iso_str: str) -> datetime:
    """ISO 8601 문자열을 datetime으로 파싱. 'Z' 접미사 처리 포함."""
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))


def parse_llm_json_response(raw: str) -> dict:
    """LLM 응답에서 JSON 파싱. 마크다운 코드 펜스 자동 제거."""
    content = raw.strip()

    if content.startswith("```"):
        parts = content.split("```")
        if len(parts) >= 2:
            content = parts[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

    return json.loads(content)
