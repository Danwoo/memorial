# backend/app/agents/tools/reflection_tools.py
"""소크라테스식 회고 및 인지 분석 tool 정의."""

from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.config.llm import get_analytical_llm, get_creative_llm

logger = logging.getLogger(__name__)

_REFLECTION_PROMPT = """다음 내용을 읽고 사용자가 깊이 생각해볼 수 있는 소크라테스식 질문 3개를 만들어주세요.

요구사항:
- 질문은 단순 사실 확인이 아니라 가치관, 감정, 동기를 탐색하는 열린 질문이어야 합니다
- 각 질문은 서로 다른 관점(감정/행동/가치관)에서 접근해야 합니다
- 질문은 판단하지 않고 탐색을 유도해야 합니다
- 한국어로 작성해주세요

Few-shot 예시:

내용: "오늘 새 프로젝트 시작했는데 잘 할 수 있을지 걱정된다. 팀원들도 잘 모르는 분야라 부담이 크다."
출력: {{"questions": [
  "이 프로젝트를 잘 해내고 싶다는 마음의 근원은 무엇인가요?",
  "처음 도전하는 분야에서 '잘한다'는 것은 당신에게 어떤 모습으로 느껴지나요?",
  "팀원들에게 솔직하게 부담을 공유한다면 어떤 일이 일어날 것 같나요?"
]}}

내용: "친구와 다툰 후 며칠째 연락을 안 했다. 먼저 연락하고 싶지만 자존심 때문에 못 하겠다."
출력: {{"questions": [
  "이 친구와의 관계가 당신에게 어떤 의미를 가지고 있나요?",
  "'자존심'이 지키려는 것은 정확히 무엇인가요?",
  "1년 뒤의 당신은 지금 어떤 선택을 하길 바랄까요?"
]}}

내용:
{content}

JSON 형식으로 출력:
{{"questions": ["질문1", "질문2", "질문3"]}}"""

_CBT_PROMPT = """사용자의 텍스트에서 인지 왜곡(cognitive distortion) 패턴을 감지하세요.

인지 왜곡 유형:
- 전부 아니면 전무 사고(all-or-nothing): "항상", "절대", "전혀" 같은 극단 단어
- 과잉 일반화: 하나의 사건을 전체로 확대
- 감정적 추론: 느낌을 사실로 취급 ("불안하니까 실제로 위험해")
- 자기 비난: 통제 불가능한 일까지 자기 탓
- 파국화: 최악의 결과만 상상
- 독심술: 근거 없이 타인의 생각을 단정
- 레이블링: 자신/타인에게 부정적 정체성 부여

Few-shot 예시:

텍스트: "오늘 발표 망쳤어. 나는 항상 이런 식이야. 영원히 발표 못 할 거야."
출력: {{"detected": true, "type": "all-or-nothing", "hint": "정말 '항상' 그랬는지, 잘했던 발표를 떠올려볼 수 있을까요?"}}

텍스트: "이번 프로젝트 결과가 좋지 않으면 나는 그냥 실패자야."
출력: {{"detected": true, "type": "labeling", "hint": "한 번의 결과가 사람의 정체성을 정의할 수 있다고 느끼는 이유는 무엇인가요?"}}

텍스트: "팀장이 회의에서 표정이 안 좋았어. 분명 내 발표가 마음에 안 든 거야."
출력: {{"detected": true, "type": "mind-reading", "hint": "표정 외에 그렇게 해석할 수 있는 다른 단서가 있었나요?"}}

텍스트: "오늘은 산책하면서 좋은 아이디어가 떠올랐어."
출력: {{"detected": false, "type": null, "hint": null}}

텍스트: "면접에서 떨어지면 내 인생은 끝장이야."
출력: {{"detected": true, "type": "catastrophizing", "hint": "이번 결과 외에 다른 가능성도 함께 생각해본다면 어떤 것들이 있을까요?"}}

텍스트:
{text}

JSON 형식으로 출력:
{{"detected": true/false, "type": "왜곡 유형 또는 null", "hint": "소크라테스식 반문 힌트 1문장 또는 null"}}"""

_DRAFT_PROMPT = """다음 대화 요약을 바탕으로 사용자가 일기에 쓸 수 있는 초안을 작성해주세요.

대화 요약:
{conversation_summary}

요구사항:
- 1인칭 시점으로 작성해주세요 ("나는...", "오늘...")
- 대화에서 나온 감정, 통찰, 깨달음을 자연스럽게 녹여주세요
- 300~500자 분량의 일기 초안을 작성해주세요
- 형식적이지 않고 솔직하고 개인적인 어조로 작성해주세요
- 한국어로 작성해주세요

일기 초안만 출력하세요. 부가 설명 없이 일기 내용만 작성해주세요."""


@tool
async def generate_reflection_questions(
    content: str,
    *,
    config: RunnableConfig,
) -> list[str]:
    """일기 또는 대화 내용을 바탕으로 소크라테스식 회고 질문 3개를 생성한다.

    Args:
        content: 질문을 생성할 일기 또는 대화 내용

    Returns:
        소크라테스식 회고 질문 문자열 3개의 리스트
    """
    try:
        llm = get_creative_llm()
        llm_with_json = llm.bind(response_format={"type": "json_object"})
        prompt = _REFLECTION_PROMPT.format(content=content[:1500])
        response = await llm_with_json.ainvoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        result = json.loads(raw)
        questions = result.get("questions", [])
        if isinstance(questions, list) and len(questions) >= 1:
            return questions[:3]
        return [raw]
    except Exception:
        logger.warning("회고 질문 생성 실패, 기본값 반환")
        return [
            "오늘 경험한 것 중 가장 의미 있었던 순간은 무엇인가요?",
            "이 상황에서 나의 감정은 무엇을 말해주고 있나요?",
            "이 경험을 통해 나 자신에 대해 무엇을 알게 되었나요?",
        ]


@tool
async def detect_cognitive_distortions(
    text: str,
    *,
    config: RunnableConfig,
) -> dict:
    """텍스트에서 CBT 기반 인지 왜곡 패턴을 감지한다.

    Args:
        text: 분석할 사용자 텍스트

    Returns:
        detected(감지 여부), type(왜곡 유형 또는 None), hint(소크라테스식 반문 힌트 또는 None) 필드를 가진 dict
    """
    try:
        llm = get_analytical_llm()
        llm_with_json = llm.bind(response_format={"type": "json_object"})
        prompt = _CBT_PROMPT.format(text=text[:500])
        response = await llm_with_json.ainvoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        result = json.loads(raw)
        return {
            "detected": bool(result.get("detected", False)),
            "type": result.get("type") or None,
            "hint": result.get("hint") or None,
        }
    except Exception:
        logger.warning("인지 왜곡 감지 실패, 기본값 반환")
        return {"detected": False, "type": None, "hint": None}


@tool
async def generate_diary_draft(
    conversation_summary: str,
    *,
    config: RunnableConfig,
) -> str:
    """대화 요약을 바탕으로 일기 초안을 생성한다.

    Args:
        conversation_summary: 소크라테스 대화 내용 요약

    Returns:
        1인칭 시점의 일기 초안 텍스트
    """
    try:
        llm = get_creative_llm()
        prompt = _DRAFT_PROMPT.format(conversation_summary=conversation_summary[:2000])
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        draft = response.content.strip()
        if not draft:
            raise ValueError("LLM이 빈 응답을 반환했습니다")
        return draft
    except Exception:
        logger.warning("일기 초안 생성 실패, 기본값 반환")
        return (
            "오늘 소크라테스와 나눈 대화를 돌아보며 많은 것을 느꼈다. 대화를 통해 나 자신을 더 깊이 이해할 수 있었다."
        )
