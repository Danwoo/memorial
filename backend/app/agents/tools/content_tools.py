# backend/app/agents/tools/content_tools.py
"""콘텐츠 처리 도구 모음 — Scribe 에이전트 전용 LLM 기반 tool 5종."""

import json
import logging
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.config.llm import get_analytical_llm, get_creative_llm, get_tagger_llm
from app.utils import parse_llm_json_response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 모듈 레벨 프롬프트 상수
# ---------------------------------------------------------------------------

_CLASSIFY_SYSTEM = """당신은 콘텐츠 분류 전문가입니다.
주어진 텍스트를 다음 세 카테고리 중 하나로 분류하고 신뢰도를 반환하세요.

카테고리:
- INSIGHT: 의견, 에세이, 분석, 개인적 통찰
- FACT: 문서, 설명서, 뉴스, 참고 정보
- SPAM: 광고, 내비게이션 텍스트, 무관한 내용

반드시 아래 JSON 형식으로만 응답하세요. 마크다운 없음.
{
  "category": "INSIGHT" | "FACT" | "SPAM",
  "confidence": 0.0 ~ 1.0
}"""

_SUMMARIZE_SYSTEM = """당신은 텍스트 요약 전문가입니다.
주어진 텍스트의 핵심 주장과 결론을 한국어로 2~3문장으로 요약하세요.
요약문만 반환하고 다른 설명은 붙이지 마세요."""

_EXTRACT_TAGS_SYSTEM = """당신은 키워드 태그 추출 전문가입니다.
주어진 텍스트에서 핵심 주제를 나타내는 태그를 추출하세요.
태그는 영어 또는 한국어 명사형으로, 구체적이고 검색에 유용한 단어를 선택합니다.

반드시 아래 JSON 형식으로만 응답하세요. 마크다운 없음.
{
  "tags": ["태그1", "태그2", ...]
}"""

_SENTIMENT_SYSTEM = """당신은 감정 분석 전문가입니다.
주어진 텍스트의 감정을 분석하여 다음 JSON 형식으로만 반환하세요. 마크다운 없음.
{
  "sentiment": "positive" | "negative" | "neutral",
  "mood": "기쁨" | "슬픔" | "분노" | "불안" | "평온" | null,
  "intensity": 0.0 ~ 1.0
}

- sentiment: 전반적인 긍정/부정/중립
- mood: 구체적인 감정 단어 (한국어). 감정이 뚜렷하지 않으면 null
- intensity: 감정의 강도 (0=매우 약함, 1=매우 강함)"""

_INLINE_EDIT_SYSTEM_TEMPLATES: dict[str, str] = {
    "expand": "당신은 글쓰기 보조 전문가입니다. 주어진 텍스트를 더 풍부하게 확장하세요. 원문의 의도와 어조를 유지하면서 세부 내용, 예시, 설명을 추가합니다. 수정된 텍스트만 반환하세요.",
    "shorten": "당신은 글쓰기 보조 전문가입니다. 주어진 텍스트를 핵심만 남기고 간결하게 줄이세요. 중요한 정보는 유지하되 불필요한 반복과 장황함을 제거합니다. 수정된 텍스트만 반환하세요.",
    "polish": "당신은 글쓰기 보조 전문가입니다. 주어진 텍스트의 표현을 다듬고 어색한 부분을 자연스럽게 개선하세요. 내용은 그대로 유지하면서 가독성과 문체를 향상시킵니다. 수정된 텍스트만 반환하세요.",
    "formal": "당신은 글쓰기 보조 전문가입니다. 주어진 텍스트를 공식적이고 격식체로 변환하세요. 구어체 표현을 문어체로, 비격식적 표현을 격식적으로 바꿉니다. 수정된 텍스트만 반환하세요.",
    "casual": "당신은 글쓰기 보조 전문가입니다. 주어진 텍스트를 자연스럽고 친근한 구어체로 변환하세요. 격식적인 표현을 일상적이고 편안한 말투로 바꿉니다. 수정된 텍스트만 반환하세요.",
}


# ---------------------------------------------------------------------------
# Tool 정의
# ---------------------------------------------------------------------------


@tool
async def classify_content(
    text: str,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """텍스트 콘텐츠를 INSIGHT/FACT/SPAM 중 하나로 분류하고 신뢰도를 반환한다.

    Args:
        text: 분류할 텍스트

    Returns:
        category("INSIGHT"|"FACT"|"SPAM")와 confidence(float) 필드를 가진 dict
    """
    base_llm = get_analytical_llm()
    llm = base_llm.bind(response_format={"type": "json_object"})

    messages = [
        SystemMessage(content=_CLASSIFY_SYSTEM),
        HumanMessage(content=text),
    ]

    try:
        response = await llm.ainvoke(messages)
        result = parse_llm_json_response(response.content.strip())
        return {
            "category": result.get("category", "FACT"),
            "confidence": float(result.get("confidence", 0.5)),
        }
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logger.warning("classify_content JSON 파싱 실패: %s", e)
        return {"category": "FACT", "confidence": 0.5}
    except Exception as e:
        logger.error("classify_content 오류: %s", e)
        return {"category": "FACT", "confidence": 0.0}


@tool
async def summarize_content(
    text: str,
    *,
    config: RunnableConfig,
) -> str:
    """텍스트를 한국어 2~3문장으로 요약한다.

    Args:
        text: 요약할 텍스트

    Returns:
        한국어 2~3문장 요약문
    """
    base_llm = get_analytical_llm()

    messages = [
        SystemMessage(content=_SUMMARIZE_SYSTEM),
        HumanMessage(content=text),
    ]

    try:
        response = await base_llm.ainvoke(messages)
        return response.content.strip()
    except Exception as e:
        logger.error("summarize_content 오류: %s", e)
        return ""


@tool
async def extract_tags(
    text: str,
    max_tags: int = 5,
    *,
    config: RunnableConfig,
) -> list[str]:
    """텍스트에서 핵심 키워드 태그를 추출한다.

    Args:
        text: 태그를 추출할 텍스트
        max_tags: 최대 태그 수 (기본 5)

    Returns:
        키워드 태그 문자열 리스트
    """
    tagger_llm = get_tagger_llm()
    llm = tagger_llm.bind(response_format={"type": "json_object"})

    prompt = f"{_EXTRACT_TAGS_SYSTEM}\n\n최대 {max_tags}개의 태그를 추출하세요."
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=text),
    ]

    try:
        response = await llm.ainvoke(messages)
        result = parse_llm_json_response(response.content.strip())
        tags = result.get("tags", [])
        if not isinstance(tags, list):
            return []
        return [str(t) for t in tags[:max_tags]]
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logger.warning("extract_tags JSON 파싱 실패: %s", e)
        return []
    except Exception as e:
        logger.error("extract_tags 오류: %s", e)
        return []


@tool
async def analyze_sentiment(
    text: str,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """텍스트의 감정(긍정/부정/중립)과 구체적인 감정 상태, 강도를 분석한다.

    Args:
        text: 감정을 분석할 텍스트

    Returns:
        sentiment("positive"|"negative"|"neutral"), mood(str|None), intensity(float) 필드를 가진 dict
    """
    base_llm = get_analytical_llm()
    llm = base_llm.bind(response_format={"type": "json_object"})

    messages = [
        SystemMessage(content=_SENTIMENT_SYSTEM),
        HumanMessage(content=text),
    ]

    try:
        response = await llm.ainvoke(messages)
        result = parse_llm_json_response(response.content.strip())

        sentiment = result.get("sentiment", "neutral")
        if sentiment not in ("positive", "negative", "neutral"):
            sentiment = "neutral"

        mood = result.get("mood")
        if mood is not None and not isinstance(mood, str):
            mood = None

        intensity = float(result.get("intensity", 0.5))
        intensity = max(0.0, min(1.0, intensity))

        return {"sentiment": sentiment, "mood": mood, "intensity": intensity}
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logger.warning("analyze_sentiment JSON 파싱 실패: %s", e)
        return {"sentiment": "neutral", "mood": None, "intensity": 0.0}
    except Exception as e:
        logger.error("analyze_sentiment 오류: %s", e)
        return {"sentiment": "neutral", "mood": None, "intensity": 0.0}


@tool
async def inline_edit(
    text: str,
    action: Literal["expand", "shorten", "polish", "formal", "casual"] = "polish",
    *,
    config: RunnableConfig,
) -> str:
    """텍스트를 지정된 방식으로 인라인 편집한다.

    Args:
        text: 편집할 원문 텍스트
        action: 편집 방식.
            - expand: 내용 확장 (세부 내용 추가)
            - shorten: 내용 압축 (핵심만 남김)
            - polish: 표현 다듬기 (어색한 부분 개선)
            - formal: 격식체로 변환
            - casual: 구어체로 변환

    Returns:
        편집된 텍스트
    """
    system_prompt = _INLINE_EDIT_SYSTEM_TEMPLATES.get(action, _INLINE_EDIT_SYSTEM_TEMPLATES["polish"])
    base_llm = get_creative_llm()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=text),
    ]

    try:
        response = await base_llm.ainvoke(messages)
        return response.content.strip()
    except Exception as e:
        logger.error("inline_edit 오류 (action=%s): %s", action, e)
        return text
