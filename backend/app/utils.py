"""
Shared Utility Functions
Common helpers used across services, repositories, and agents.
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_iso_datetime(iso_str: str) -> datetime:
    """Parse ISO 8601 datetime string, handling 'Z' suffix.

    Args:
        iso_str: ISO datetime string (e.g. "2024-01-15T10:30:00Z")

    Returns:
        Timezone-aware datetime object.

    Raises:
        ValueError: If the string cannot be parsed.
    """
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))


def parse_llm_json_response(raw: str) -> dict:
    """Parse JSON from an LLM response, stripping markdown code fences.

    Handles responses like:
        ```json
        {"key": "value"}
        ```

    Args:
        raw: Raw LLM response text.

    Returns:
        Parsed dict.

    Raises:
        json.JSONDecodeError: If JSON parsing fails after stripping.
    """
    content = raw.strip()

    if content.startswith("```"):
        # Split on ``` and take the content block
        parts = content.split("```")
        if len(parts) >= 2:
            content = parts[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

    return json.loads(content)
