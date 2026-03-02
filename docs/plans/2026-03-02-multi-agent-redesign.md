# Multi-Agent System Architecture Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 7개 전문 에이전트(Supervisor/Socrates/Librarian/Analyst/Scribe/Curator/Reporter)가 51개 tool을 통해 5개 화면을 서비스하는 실제 multi-agent ReAct 시스템으로 전환.

**Architecture:** 현재 고정 DAG 파이프라인(query_understanding→retrieval→grading→enrichment→assembly)을 LangGraph `create_react_agent` 기반 ReAct 에이전트로 전환. Tool들은 `@tool` 데코레이터로 정의되며 `RunnableConfig.configurable["user_id"]`를 통해 보안 컨텍스트를 주입받음. `astream_events(version="v2")`로 전환하여 tool 호출 과정을 SSE로 실시간 스트리밍.

**Tech Stack:** LangGraph (create_react_agent, astream_events), LangChain (@tool, RunnableConfig), FastAPI SSE, React TypeScript, KuzuDB (GraphRAG multi-hop)

---

## Sprint 1: Tool Infrastructure (Foundation)

### Task 1.1: Tool 디렉토리 구조 및 base context 설정

**Files:**
- Create: `backend/app/agents/tools/__init__.py`
- Create: `backend/app/agents/tools/_context.py`

**Step 1: `_context.py` 작성 — user_id 자동 주입 헬퍼**

```python
# backend/app/agents/tools/_context.py
"""Tool 실행 시 RunnableConfig에서 user_id를 추출하는 유틸리티."""
from langchain_core.runnables import RunnableConfig


def get_user_id(config: RunnableConfig) -> str:
    """RunnableConfig의 configurable에서 user_id를 추출한다."""
    user_id = (config.get("configurable") or {}).get("user_id")
    if not user_id:
        raise ValueError("user_id가 config.configurable에 없습니다.")
    return user_id
```

**Step 2: `__init__.py` 빈 파일로 생성 (추후 채움)**

```python
# backend/app/agents/tools/__init__.py
"""Memoir AI 에이전트 tool registry."""
```

**Step 3: Python 구문 검증**

```bash
cd backend && python -c "from app.agents.tools._context import get_user_id; print('OK')"
```
Expected: `OK`

**Step 4: 커밋**

```bash
git add backend/app/agents/tools/
git commit -m "feat: tool infrastructure 디렉토리 생성 + user_id context 헬퍼 (S10-1)"
```

---

### Task 1.2: Retrieval Tools

**Files:**
- Create: `backend/app/agents/tools/retrieval_tools.py`

**Step 1: 파일 작성**

```python
# backend/app/agents/tools/retrieval_tools.py
"""스크랩/그래프 검색 tool 정의."""
from __future__ import annotations
from typing import Any
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from app.agents.tools._context import get_user_id
from app.agents.container import get_agent_container


@tool
async def search_scraps(
    query: str,
    limit: int = 5,
    tags: list[str] | None = None,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """사용자의 저장된 스크랩에서 관련 내용을 하이브리드 검색(Dense+Sparse+Graph)합니다.

    Args:
        query: 검색 쿼리 (한국어/영어 모두 지원)
        limit: 반환할 최대 결과 수 (기본 5)
        tags: 태그 필터 (선택)

    Returns:
        스크랩 목록 (id, title, content_preview, tags, source_type, created_at, score)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    results = await container.hybrid_search.search(
        query=query,
        user_id=user_id,
        limit=limit,
        tags=tags,
    )
    return [
        {
            "id": r.get("id"),
            "title": r.get("title", ""),
            "content_preview": (r.get("content") or "")[:300],
            "tags": r.get("tags", []),
            "source_type": r.get("source_type", "text"),
            "created_at": str(r.get("created_at", "")),
            "score": r.get("rrf_score", 0.0),
        }
        for r in results
    ]


@tool
async def search_graph_entities(
    keyword: str,
    entity_type: str | None = None,
    limit: int = 10,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """지식 그래프에서 엔티티를 검색합니다.

    Args:
        keyword: 검색 키워드
        entity_type: 엔티티 타입 필터 (Concept/Person/Organization/Technology 등, 선택)
        limit: 최대 결과 수

    Returns:
        엔티티 목록 (name, type, related_count)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    results = await container.mindmap_repo.search_entities(
        keyword=keyword,
        user_id=user_id,
        entity_type=entity_type,
        limit=limit,
    )
    return results


@tool
async def get_graph_context(
    topic: str,
    depth: int = 2,
    rel_type: str | None = None,
    limit: int = 20,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """지식 그래프에서 특정 주제의 연관 컨텍스트를 multi-hop 탐색으로 가져옵니다.

    Args:
        topic: 탐색 시작 엔티티 이름
        depth: 탐색 깊이 (1-3, 기본 2)
        rel_type: 관계 타입 필터 (RELATED_TO/PART_OF 등, 선택)
        limit: 최대 관련 엔티티 수

    Returns:
        entities(list), relations(list), source_scraps(list)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    context = await container.mindmap_repo.get_related_context(
        topic=topic,
        user_id=user_id,
        depth=min(depth, 3),
        rel_type=rel_type,
        limit=limit,
    )
    return context
```

**Step 2: Python 구문 검증**

```bash
cd backend && python -c "import ast; ast.parse(open('app/agents/tools/retrieval_tools.py', encoding='utf-8').read()); print('OK')"
```
Expected: `OK`

**Step 3: 커밋**

```bash
git add backend/app/agents/tools/retrieval_tools.py
git commit -m "feat: retrieval tools (search_scraps, search_graph_entities, get_graph_context) (S10-2)"
```

---

### Task 1.3: Diary Tools

**Files:**
- Create: `backend/app/agents/tools/diary_tools.py`

**Step 1: 파일 작성**

```python
# backend/app/agents/tools/diary_tools.py
"""일기 관련 tool 정의."""
from __future__ import annotations
from typing import Any
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from app.agents.tools._context import get_user_id
from app.agents.container import get_agent_container


@tool
async def search_diaries(
    query: str,
    limit: int = 5,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """사용자의 일기에서 내용을 검색합니다.

    Args:
        query: 검색 쿼리
        limit: 최대 결과 수

    Returns:
        일기 목록 (id, title, content_preview, mood, tags, created_at)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    results = await container.diary_repo.search_diaries(
        query=query,
        user_id=user_id,
        limit=limit,
    )
    return [
        {
            "id": str(r.get("id", "")),
            "title": r.get("title", ""),
            "content_preview": (r.get("content") or "")[:400],
            "mood": r.get("mood"),
            "tags": r.get("tags", []),
            "created_at": str(r.get("created_at", "")),
        }
        for r in results
    ]


@tool
async def get_diary_detail(
    diary_id: str,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """특정 일기의 전체 내용을 가져옵니다.

    Args:
        diary_id: 일기 ID

    Returns:
        일기 전체 내용 (id, title, content, mood, tags, created_at)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    diary = await container.diary_repo.get_diary_by_id(
        diary_id=diary_id,
        user_id=user_id,
    )
    if not diary:
        return {"error": f"일기 {diary_id}를 찾을 수 없습니다."}
    return {
        "id": str(diary.get("id", "")),
        "title": diary.get("title", ""),
        "content": diary.get("content", ""),
        "mood": diary.get("mood"),
        "tags": diary.get("tags", []),
        "created_at": str(diary.get("created_at", "")),
    }


@tool
async def get_emotion_trend(
    days: int = 7,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """최근 N일간의 감정 추세를 가져옵니다.

    Args:
        days: 조회 기간 (일, 기본 7)

    Returns:
        날짜별 감정 목록 (date, mood, tags, diary_count)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    trend = await container.diary_repo.get_emotion_trend(
        user_id=user_id,
        days=days,
    )
    return trend


@tool
async def list_diary_dates(
    limit: int = 30,
    *,
    config: RunnableConfig,
) -> list[str]:
    """일기를 작성한 날짜 목록을 가져옵니다.

    Args:
        limit: 최대 날짜 수 (기본 30)

    Returns:
        날짜 문자열 목록 (YYYY-MM-DD 형식, 최신순)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    dates = await container.diary_repo.list_diary_dates(
        user_id=user_id,
        limit=limit,
    )
    return dates


@tool
async def get_diary_statistics(
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """일기 작성 통계를 가져옵니다.

    Returns:
        total_count, avg_per_week, current_streak, longest_streak, mood_distribution
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    stats = await container.diary_repo.get_diary_statistics(user_id=user_id)
    return stats
```

**Step 2: Python 구문 검증**

```bash
cd backend && python -c "import ast; ast.parse(open('app/agents/tools/diary_tools.py', encoding='utf-8').read()); print('OK')"
```

**Step 3: 커밋**

```bash
git add backend/app/agents/tools/diary_tools.py
git commit -m "feat: diary tools (search/detail/emotion/stats) (S10-3)"
```

---

### Task 1.4: Reflection Tools (Socrates 전용)

**Files:**
- Create: `backend/app/agents/tools/reflection_tools.py`

**Step 1: 파일 작성**

```python
# backend/app/agents/tools/reflection_tools.py
"""소크라테스식 회고 및 인지 분석 tool 정의."""
from __future__ import annotations
from typing import Any
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from app.core.llm import get_llm


_REFLECTION_PROMPT = """당신은 소크라테스식 대화 전문가입니다.
다음 일기/대화 내용을 바탕으로 깊은 성찰을 유도하는 질문 3개를 생성하세요.

내용:
{content}

규칙:
- 판단 없이 탐구하는 열린 질문
- 감정과 가정을 탐색하도록 유도
- 한국어로 작성

JSON 형식으로 반환:
{{"questions": ["질문1", "질문2", "질문3"]}}"""

_CBT_PROMPT = """당신은 인지행동치료(CBT) 전문가입니다.
다음 텍스트에서 인지 왜곡을 탐지하세요.

텍스트: {text}

인지 왜곡 유형: 흑백논리, 과잉일반화, 재앙화, 개인화, 독심술, 감정적 추론, 선택적 추상화

JSON 형식으로 반환:
{{"detected": true/false, "type": "왜곡유형 또는 null", "hint": "부드러운 재구성 힌트 또는 null"}}"""

_DRAFT_PROMPT = """다음 대화를 바탕으로 오늘의 일기 초안을 작성하세요.

대화:
{conversation}

규칙:
- 1인칭 시점
- 감정과 경험 중심
- 300-500자 한국어
- 자연스러운 일기 문체"""


@tool
async def generate_reflection_questions(
    content: str,
    *,
    config: RunnableConfig,
) -> list[str]:
    """일기나 대화 내용을 바탕으로 소크라테스식 성찰 질문을 생성합니다.

    Args:
        content: 분석할 일기 또는 대화 내용

    Returns:
        성찰 질문 3개
    """
    import json
    llm = get_llm(mode="creative")
    prompt = _REFLECTION_PROMPT.format(content=content[:2000])
    response = await llm.ainvoke(prompt)
    try:
        data = json.loads(response.content)
        return data.get("questions", [])
    except Exception:
        return [response.content]


@tool
async def detect_cognitive_distortions(
    text: str,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """텍스트에서 인지 왜곡(CBT)을 탐지합니다.

    Args:
        text: 분석할 텍스트

    Returns:
        detected(bool), type(str|None), hint(str|None)
    """
    import json
    llm = get_llm(mode="analytical")
    prompt = _CBT_PROMPT.format(text=text[:1000])
    response = await llm.ainvoke(prompt)
    try:
        return json.loads(response.content)
    except Exception:
        return {"detected": False, "type": None, "hint": None}


@tool
async def generate_diary_draft(
    conversation_summary: str,
    *,
    config: RunnableConfig,
) -> str:
    """대화 요약을 바탕으로 일기 초안을 생성합니다.

    Args:
        conversation_summary: 대화 내용 요약 (최근 대화 내용)

    Returns:
        일기 초안 텍스트
    """
    llm = get_llm(mode="creative")
    prompt = _DRAFT_PROMPT.format(conversation=conversation_summary[:3000])
    response = await llm.ainvoke(prompt)
    return response.content
```

**Step 2: 구문 검증**

```bash
cd backend && python -c "import ast; ast.parse(open('app/agents/tools/reflection_tools.py', encoding='utf-8').read()); print('OK')"
```

**Step 3: 커밋**

```bash
git add backend/app/agents/tools/reflection_tools.py
git commit -m "feat: reflection tools (소크라테스 질문/CBT/일기초안) (S10-4)"
```

---

### Task 1.5: Content Tools (Scribe 전용)

**Files:**
- Create: `backend/app/agents/tools/content_tools.py`

**Step 1: 파일 작성**

```python
# backend/app/agents/tools/content_tools.py
"""콘텐츠 처리 tool 정의 (분류/요약/태깅/감정분석/인라인편집)."""
from __future__ import annotations
from typing import Any, Literal
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from app.core.llm import get_llm, get_tagger_llm


_CLASSIFY_PROMPT = """다음 텍스트를 분류하세요.

텍스트: {text}

분류:
- INSIGHT: 인사이트, 아이디어, 의견, 분석
- FACT: 사실, 정보, 데이터, 지식
- SPAM: 광고, 무관한 내용, 의미 없는 텍스트

JSON: {{"category": "INSIGHT|FACT|SPAM", "confidence": 0.0-1.0}}"""

_SUMMARIZE_PROMPT = """다음 텍스트를 2-3문장으로 한국어 요약하세요.

텍스트: {text}

핵심 내용만 담아 간결하게 요약하세요."""

_SENTIMENT_PROMPT = """다음 텍스트의 감정을 분석하세요.

텍스트: {text}

JSON: {{"sentiment": "positive|negative|neutral", "mood": "기쁨|슬픔|분노|불안|평온|설렘|피로 중 하나 또는 null", "intensity": 0.0-1.0}}"""

_INLINE_PROMPTS = {
    "expand": "다음 텍스트를 2-3배 분량으로 자연스럽게 확장하세요:\n{text}",
    "shorten": "다음 텍스트를 절반 이하로 핵심만 남겨 요약하세요:\n{text}",
    "polish": "다음 텍스트의 문체를 자연스럽고 매끄럽게 다듬으세요:\n{text}",
    "formal": "다음 텍스트를 격식체로 변환하세요:\n{text}",
    "casual": "다음 텍스트를 친근한 구어체로 변환하세요:\n{text}",
}


@tool
async def classify_content(
    text: str,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """텍스트를 INSIGHT/FACT/SPAM으로 분류합니다.

    Args:
        text: 분류할 텍스트

    Returns:
        category(str), confidence(float)
    """
    import json
    llm = get_llm(mode="analytical")
    prompt = _CLASSIFY_PROMPT.format(text=text[:2000])
    response = await llm.ainvoke(prompt)
    try:
        return json.loads(response.content)
    except Exception:
        return {"category": "FACT", "confidence": 0.5}


@tool
async def summarize_content(
    text: str,
    *,
    config: RunnableConfig,
) -> str:
    """텍스트를 2-3문장으로 한국어 요약합니다.

    Args:
        text: 요약할 텍스트

    Returns:
        요약 텍스트
    """
    llm = get_llm(mode="analytical")
    prompt = _SUMMARIZE_PROMPT.format(text=text[:4000])
    response = await llm.ainvoke(prompt)
    return response.content


@tool
async def extract_tags(
    text: str,
    max_tags: int = 5,
    *,
    config: RunnableConfig,
) -> list[str]:
    """텍스트에서 키워드 태그를 추출합니다.

    Args:
        text: 태그를 추출할 텍스트
        max_tags: 최대 태그 수 (기본 5)

    Returns:
        태그 목록
    """
    import json
    llm = get_tagger_llm()
    prompt = f"다음 텍스트에서 핵심 키워드 {max_tags}개를 추출하세요.\n텍스트: {text[:2000]}\nJSON: {{\"tags\": [\"tag1\", \"tag2\"]}}"
    response = await llm.ainvoke(prompt)
    try:
        data = json.loads(response.content)
        return data.get("tags", [])[:max_tags]
    except Exception:
        return []


@tool
async def analyze_sentiment(
    text: str,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """텍스트의 감정을 분석합니다.

    Args:
        text: 분석할 텍스트

    Returns:
        sentiment(positive|negative|neutral), mood(str|None), intensity(float)
    """
    import json
    llm = get_llm(mode="analytical")
    prompt = _SENTIMENT_PROMPT.format(text=text[:1000])
    response = await llm.ainvoke(prompt)
    try:
        return json.loads(response.content)
    except Exception:
        return {"sentiment": "neutral", "mood": None, "intensity": 0.5}


@tool
async def inline_edit(
    text: str,
    action: Literal["expand", "shorten", "polish", "formal", "casual"] = "polish",
    *,
    config: RunnableConfig,
) -> str:
    """텍스트를 지정된 방식으로 인라인 편집합니다.

    Args:
        text: 편집할 텍스트
        action: 편집 방식 (expand/shorten/polish/formal/casual)

    Returns:
        편집된 텍스트
    """
    llm = get_llm(mode="creative")
    prompt_template = _INLINE_PROMPTS.get(action, _INLINE_PROMPTS["polish"])
    prompt = prompt_template.format(text=text[:3000])
    response = await llm.ainvoke(prompt)
    return response.content
```

**Step 2: 구문 검증**

```bash
cd backend && python -c "import ast; ast.parse(open('app/agents/tools/content_tools.py', encoding='utf-8').read()); print('OK')"
```

**Step 3: 커밋**

```bash
git add backend/app/agents/tools/content_tools.py
git commit -m "feat: content tools (classify/summarize/tags/sentiment/inline_edit) (S10-5)"
```

---

### Task 1.6: Graph Tools (Curator 전용)

**Files:**
- Create: `backend/app/agents/tools/graph_tools.py`

**Step 1: 파일 작성**

```python
# backend/app/agents/tools/graph_tools.py
"""지식 그래프 관리 tool 정의 (엔티티 추출/관계/저장/검증)."""
from __future__ import annotations
from typing import Any
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from app.agents.tools._context import get_user_id
from app.agents.container import get_agent_container
from app.core.llm import get_llm


_ENTITY_PROMPT = """다음 텍스트에서 Named Entity를 추출하세요.

텍스트: {text}

허용 타입: Concept, Person, Organization, Location, Event, Technology, Product, Topic, Idea, Company, Platform, Framework, Language, Tool, Project

JSON: {{"entities": [{{"name": "이름", "type": "타입"}}]}}"""

_RELATION_PROMPT = """다음 엔티티 목록과 텍스트를 보고 엔티티 간 관계를 추출하세요.

텍스트: {text}
엔티티: {entities}

허용 관계: RELATED_TO, PART_OF, CAUSED_BY, DEPENDS_ON, SIMILAR_TO, OPPOSITE_OF, DERIVED_FROM, USED_BY, CREATED_BY, WORKS_AT, LOCATED_IN, BELONGS_TO, HAS, IS_A, USES, USED_FOR, BUILT_WITH, INSPIRED_BY, CONTAINS, SUPPORTS, CONTRADICTS, LEADS_TO

JSON: {{"relations": [{{"source": "엔티티1", "target": "엔티티2", "rel_type": "관계타입"}}]}}"""

_CONNECTION_PROMPT = """다음 엔티티들 사이에서 아직 연결되지 않은 잠재적 관계를 제안하세요.

엔티티: {entities}
기존 관계: {existing_relations}

JSON: {{"suggestions": [{{"source": "엔티티1", "target": "엔티티2", "rel_type": "관계타입", "reason": "이유"}}]}}"""


@tool
async def extract_entities(
    text: str,
    *,
    config: RunnableConfig,
) -> list[dict[str, str]]:
    """텍스트에서 Named Entity(이름, 타입)를 추출합니다.

    Args:
        text: 엔티티를 추출할 텍스트

    Returns:
        엔티티 목록 (name, type)
    """
    import json
    llm = get_llm(mode="analytical")
    prompt = _ENTITY_PROMPT.format(text=text[:3000])
    response = await llm.ainvoke(prompt)
    try:
        data = json.loads(response.content)
        return data.get("entities", [])
    except Exception:
        return []


@tool
async def extract_relations(
    text: str,
    entities: list[str],
    *,
    config: RunnableConfig,
) -> list[dict[str, str]]:
    """엔티티 간 관계를 추출합니다.

    Args:
        text: 원본 텍스트
        entities: 이미 추출된 엔티티 이름 목록

    Returns:
        관계 목록 (source, target, rel_type)
    """
    import json
    llm = get_llm(mode="analytical")
    prompt = _RELATION_PROMPT.format(
        text=text[:2000],
        entities=", ".join(entities[:20]),
    )
    response = await llm.ainvoke(prompt)
    try:
        data = json.loads(response.content)
        return data.get("relations", [])
    except Exception:
        return []


@tool
async def save_to_graph(
    source_id: str,
    source_type: Literal["scrap", "diary"],
    entities: list[dict[str, str]],
    relations: list[dict[str, str]],
    *,
    config: RunnableConfig,
) -> dict[str, int]:
    """추출된 엔티티와 관계를 KuzuDB 그래프에 저장합니다.

    Args:
        source_id: 소스 스크랩/일기 ID
        source_type: 소스 타입 ("scrap" 또는 "diary")
        entities: 엔티티 목록 (name, type)
        relations: 관계 목록 (source, target, rel_type)

    Returns:
        저장된 entities_count, relations_count
    """
    from typing import Literal
    user_id = get_user_id(config)
    container = await get_agent_container()
    result = await container.mindmap_repo.upsert_entities_and_relations(
        source_id=source_id,
        user_id=user_id,
        entities=entities,
        relations=relations,
    )
    return result


@tool
async def get_ego_graph(
    entity_name: str,
    hops: int = 2,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """특정 엔티티를 중심으로 N-hop 서브그래프를 가져옵니다.

    Args:
        entity_name: 중심 엔티티 이름
        hops: 탐색 홉 수 (1-3, 기본 2)

    Returns:
        nodes(list), edges(list)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    return await container.mindmap_repo.get_ego_graph(
        entity_name=entity_name,
        user_id=user_id,
        hops=min(hops, 3),
    )


@tool
async def get_hub_entities(
    limit: int = 10,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """가장 많은 연결을 가진 허브 엔티티 목록을 가져옵니다.

    Args:
        limit: 최대 결과 수 (기본 10)

    Returns:
        엔티티 목록 (name, type, connection_count)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    return await container.mindmap_repo.get_hub_entities(
        user_id=user_id,
        limit=limit,
    )


@tool
async def get_orphan_entities(
    limit: int = 20,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """연결이 없는 고립 엔티티 목록을 가져옵니다.

    Args:
        limit: 최대 결과 수 (기본 20)

    Returns:
        고립 엔티티 목록 (name, type)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    return await container.mindmap_repo.get_orphan_entities(
        user_id=user_id,
        limit=limit,
    )


@tool
async def suggest_connections(
    entity_names: list[str],
    *,
    config: RunnableConfig,
) -> list[dict[str, str]]:
    """AI 기반으로 엔티티 간 잠재적 연결을 제안합니다.

    Args:
        entity_names: 분석할 엔티티 이름 목록

    Returns:
        제안 목록 (source, target, rel_type, reason)
    """
    import json
    user_id = get_user_id(config)
    container = await get_agent_container()
    existing = await container.mindmap_repo.get_relations_between(
        entity_names=entity_names,
        user_id=user_id,
    )
    llm = get_llm(mode="analytical")
    prompt = _CONNECTION_PROMPT.format(
        entities=", ".join(entity_names[:15]),
        existing_relations=str(existing[:20]),
    )
    response = await llm.ainvoke(prompt)
    try:
        data = json.loads(response.content)
        return data.get("suggestions", [])
    except Exception:
        return []
```

**Step 2: 구문 검증 및 커밋**

```bash
cd backend && python -c "import ast; ast.parse(open('app/agents/tools/graph_tools.py', encoding='utf-8').read()); print('OK')"
git add backend/app/agents/tools/graph_tools.py
git commit -m "feat: graph tools (엔티티/관계 추출+저장, ego/hub/orphan) (S10-6)"
```

---

### Task 1.7: Analysis + Session + KB + Stats Tools

**Files:**
- Create: `backend/app/agents/tools/analysis_tools.py`
- Create: `backend/app/agents/tools/session_tools.py`
- Create: `backend/app/agents/tools/kb_tools.py`
- Create: `backend/app/agents/tools/stats_tools.py`

**Step 1: `analysis_tools.py` 작성**

```python
# backend/app/agents/tools/analysis_tools.py
"""패턴 분석 및 인사이트 tool 정의."""
from __future__ import annotations
from typing import Any
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from app.agents.tools._context import get_user_id
from app.agents.container import get_agent_container
from app.core.llm import get_llm


@tool
async def get_community_insights(
    keyword: str | None = None,
    limit: int = 5,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """지식 그래프 커뮤니티 클러스터의 인사이트를 가져옵니다.

    Args:
        keyword: 관련 키워드 필터 (선택)
        limit: 최대 결과 수 (기본 5)

    Returns:
        커뮤니티 목록 (summary, entity_count, keywords)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    return await container.community_summary.get_summaries(
        user_id=user_id,
        keyword=keyword,
        limit=limit,
    )


@tool
async def find_connections(
    topic_a: str,
    topic_b: str,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """두 주제 간의 연결점과 공통 엔티티를 찾습니다.

    Args:
        topic_a: 첫 번째 주제/엔티티
        topic_b: 두 번째 주제/엔티티

    Returns:
        common_entities(list), connection_path(list), similarity_score(float)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    return await container.mindmap_repo.find_connections_between(
        topic_a=topic_a,
        topic_b=topic_b,
        user_id=user_id,
    )


@tool
async def compare_content(
    content_a: str,
    content_b: str,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """두 콘텐츠의 유사점과 차이점을 비교 분석합니다.

    Args:
        content_a: 첫 번째 내용
        content_b: 두 번째 내용

    Returns:
        similarities(list), differences(list), conclusion(str)
    """
    import json
    llm = get_llm(mode="analytical")
    prompt = f"""두 내용을 비교 분석하세요.

내용 A: {content_a[:1500]}

내용 B: {content_b[:1500]}

JSON: {{"similarities": ["공통점1", "공통점2"], "differences": ["차이점1", "차이점2"], "conclusion": "종합 분석"}}"""
    response = await llm.ainvoke(prompt)
    try:
        return json.loads(response.content)
    except Exception:
        return {"similarities": [], "differences": [], "conclusion": response.content}


@tool
async def get_entity_timeline(
    entity_name: str,
    limit: int = 20,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """특정 엔티티가 언급된 시간 순서를 가져옵니다.

    Args:
        entity_name: 엔티티 이름
        limit: 최대 결과 수 (기본 20)

    Returns:
        언급 목록 (date, source_type, source_id, title_preview)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    return await container.mindmap_repo.get_entity_timeline(
        entity_name=entity_name,
        user_id=user_id,
        limit=limit,
    )


@tool
async def get_content_timeline(
    topic: str,
    limit: int = 20,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """특정 주제와 관련된 컨텐츠를 시간순으로 가져옵니다.

    Args:
        topic: 주제/태그/키워드
        limit: 최대 결과 수 (기본 20)

    Returns:
        컨텐츠 목록 (date, source_type, title, preview)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    return await container.hybrid_search.get_content_timeline(
        topic=topic,
        user_id=user_id,
        limit=limit,
    )
```

**Step 2: `session_tools.py` 작성**

```python
# backend/app/agents/tools/session_tools.py
"""대화 세션 관련 tool 정의."""
from __future__ import annotations
from typing import Any
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from app.agents.tools._context import get_user_id
from app.agents.container import get_agent_container


@tool
async def search_past_conversations(
    query: str,
    limit: int = 3,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """이전 소크라테스 대화에서 관련 맥락을 검색합니다.

    Args:
        query: 검색 쿼리
        limit: 최대 세션 수 (기본 3)

    Returns:
        세션 목록 (session_id, title, summary_preview, created_at)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    sessions = await container.socrates_repo.search_sessions_by_context(
        query=query,
        user_id=user_id,
        limit=limit,
    )
    return sessions


@tool
async def get_user_profile(
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """사용자 프로필과 관심사를 가져옵니다.

    Returns:
        interests(list), frequent_topics(list), writing_style(str)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    profile = await container.socrates_repo.get_user_profile(user_id=user_id)
    return profile or {}
```

**Step 3: `kb_tools.py` 작성**

```python
# backend/app/agents/tools/kb_tools.py
"""지식 베이스 관리 tool 정의."""
from __future__ import annotations
from typing import Any
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from app.agents.tools._context import get_user_id
from app.agents.container import get_agent_container


@tool
async def get_scrap_detail(
    scrap_id: str,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """스크랩의 전체 내용을 가져옵니다.

    Args:
        scrap_id: 스크랩 ID

    Returns:
        id, title, content, tags, source_type, url, summary, created_at
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    scrap = await container.scrap_repo.get_by_id(scrap_id=scrap_id, user_id=user_id)
    if not scrap:
        return {"error": f"스크랩 {scrap_id}를 찾을 수 없습니다."}
    return {
        "id": str(scrap.get("id", "")),
        "title": scrap.get("title", ""),
        "content": scrap.get("content", ""),
        "tags": scrap.get("tags", []),
        "source_type": scrap.get("source_type", "text"),
        "url": scrap.get("url"),
        "summary": scrap.get("summary"),
        "created_at": str(scrap.get("created_at", "")),
    }


@tool
async def list_recent_scraps(
    limit: int = 10,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """최근 저장된 스크랩 목록을 가져옵니다.

    Args:
        limit: 최대 결과 수 (기본 10)

    Returns:
        스크랩 목록 (id, title, tags, source_type, created_at)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    return await container.scrap_repo.list_recent(user_id=user_id, limit=limit)


@tool
async def list_scraps_by_tag(
    tag: str,
    limit: int = 20,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """특정 태그가 붙은 스크랩 목록을 가져옵니다.

    Args:
        tag: 필터 태그
        limit: 최대 결과 수 (기본 20)

    Returns:
        스크랩 목록 (id, title, tags, source_type, created_at)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    return await container.scrap_repo.list_by_tag(
        tag=tag, user_id=user_id, limit=limit
    )


@tool
async def update_scrap_metadata(
    scrap_id: str,
    tags: list[str] | None = None,
    summary: str | None = None,
    *,
    config: RunnableConfig,
) -> dict[str, str]:
    """스크랩의 태그와 요약을 업데이트합니다.

    Args:
        scrap_id: 스크랩 ID
        tags: 새 태그 목록 (선택)
        summary: 새 요약 (선택)

    Returns:
        status("ok" or "error"), message
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    await container.scrap_repo.update_metadata(
        scrap_id=scrap_id,
        user_id=user_id,
        tags=tags,
        summary=summary,
    )
    return {"status": "ok", "message": f"스크랩 {scrap_id} 업데이트 완료"}
```

**Step 4: `stats_tools.py` 작성**

```python
# backend/app/agents/tools/stats_tools.py
"""통계 및 활동 분석 tool 정의."""
from __future__ import annotations
from typing import Any
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from app.agents.tools._context import get_user_id
from app.agents.container import get_agent_container


@tool
async def get_knowledge_stats(
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """지식 베이스 총 통계를 가져옵니다.

    Returns:
        total_scraps, total_entities, total_relations, total_diaries, total_sessions
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    scrap_count = await container.scrap_repo.count(user_id=user_id)
    diary_count = await container.diary_repo.count(user_id=user_id)
    graph_stats = await container.mindmap_repo.get_stats(user_id=user_id)
    session_count = await container.socrates_repo.count_sessions(user_id=user_id)
    return {
        "total_scraps": scrap_count,
        "total_diaries": diary_count,
        "total_entities": graph_stats.get("entity_count", 0),
        "total_relations": graph_stats.get("relation_count", 0),
        "total_sessions": session_count,
    }


@tool
async def get_topic_distribution(
    limit: int = 10,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """관심사/태그 분포를 가져옵니다.

    Args:
        limit: 상위 N개 주제 (기본 10)

    Returns:
        주제 목록 (topic, count, percentage)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    return await container.scrap_repo.get_tag_distribution(
        user_id=user_id, limit=limit
    )


@tool
async def get_activity_streak(
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """활동 스트릭 데이터를 가져옵니다.

    Returns:
        current_streak, longest_streak, total_active_days, last_active_date
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    return await container.diary_repo.get_activity_streak(user_id=user_id)
```

**Step 5: 구문 검증 및 커밋**

```bash
cd backend && python -c "
import ast
for f in ['app/agents/tools/analysis_tools.py', 'app/agents/tools/session_tools.py', 'app/agents/tools/kb_tools.py', 'app/agents/tools/stats_tools.py']:
    ast.parse(open(f, encoding='utf-8').read())
print('All OK')
"
git add backend/app/agents/tools/
git commit -m "feat: analysis/session/kb/stats tools 완성 (S10-7)"
```

---

### Task 1.8: Report Tools + Delegation Tools

**Files:**
- Create: `backend/app/agents/tools/report_tools.py`
- Create: `backend/app/agents/tools/delegation_tools.py`

**Step 1: `report_tools.py` 작성**

```python
# backend/app/agents/tools/report_tools.py
"""보고서 생성 tool 정의."""
from __future__ import annotations
from typing import Any
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from app.agents.tools._context import get_user_id
from app.agents.container import get_agent_container


@tool
async def generate_daily_digest(
    date: str | None = None,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """오늘의 활동 요약과 AI 질문이 포함된 디제스트를 생성합니다.

    Args:
        date: 날짜 (YYYY-MM-DD, 기본 오늘)

    Returns:
        digest_text, ai_questions(list), stats
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    from app.services.digest_service import DigestService
    service = DigestService(
        diary_repo=container.diary_repo,
        scrap_repo=container.scrap_repo,
        socrates_repo=container.socrates_repo,
    )
    return await service.generate_daily_digest(user_id=user_id, date=date)


@tool
async def generate_daily_insights(
    date: str | None = None,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """일일 인사이트를 생성합니다 (패턴 발견, 행동 제안).

    Args:
        date: 날짜 (YYYY-MM-DD, 기본 오늘)

    Returns:
        인사이트 목록 (type, title, description, action_suggestion)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    from app.services.insight_service import InsightService
    service = InsightService(
        diary_repo=container.diary_repo,
        scrap_repo=container.scrap_repo,
        mindmap_repo=container.mindmap_repo,
    )
    return await service.generate_daily_insights(user_id=user_id, date=date)


@tool
async def generate_weekly_report(
    week_offset: int = 0,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """주간 활동 요약 리포트를 생성합니다.

    Args:
        week_offset: 몇 주 전 (0=이번 주, 1=지난 주)

    Returns:
        summary, highlights(list), stats, top_topics(list)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    from app.services.report_service import ReportService
    service = ReportService(
        diary_repo=container.diary_repo,
        scrap_repo=container.scrap_repo,
    )
    return await service.generate_weekly_report(
        user_id=user_id, week_offset=week_offset
    )


@tool
async def generate_monthly_report(
    month_offset: int = 0,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """월간 리포트를 생성합니다.

    Args:
        month_offset: 몇 달 전 (0=이번 달, 1=지난 달)

    Returns:
        summary, growth_stats, highlights(list), top_entities(list)
    """
    user_id = get_user_id(config)
    container = await get_agent_container()
    from app.services.report_service import ReportService
    service = ReportService(
        diary_repo=container.diary_repo,
        scrap_repo=container.scrap_repo,
    )
    return await service.generate_monthly_report(
        user_id=user_id, month_offset=month_offset
    )
```

**Step 2: `delegation_tools.py` 작성**

```python
# backend/app/agents/tools/delegation_tools.py
"""에이전트 간 위임 tool 정의. max delegation_depth=2로 순환 방지."""
from __future__ import annotations
from typing import Any
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from app.agents.tools._context import get_user_id


_MAX_DELEGATION_DEPTH = 2


def _get_delegation_depth(config: RunnableConfig) -> int:
    """현재 위임 깊이를 반환한다."""
    return (config.get("configurable") or {}).get("delegation_depth", 0)


def _make_sub_config(config: RunnableConfig, target_agent: str) -> RunnableConfig:
    """서브에이전트 실행을 위한 RunnableConfig를 생성한다."""
    configurable = dict(config.get("configurable") or {})
    configurable["delegation_depth"] = _get_delegation_depth(config) + 1
    configurable["calling_agent"] = target_agent
    return RunnableConfig(configurable=configurable)


@tool
async def delegate_to_librarian(
    query: str,
    context: str = "",
    *,
    config: RunnableConfig,
) -> str:
    """Librarian 에이전트에게 지식 검색을 위임합니다.

    Args:
        query: 검색 질문
        context: 추가 맥락 (선택)

    Returns:
        Librarian의 검색 결과 요약
    """
    if _get_delegation_depth(config) >= _MAX_DELEGATION_DEPTH:
        return "위임 깊이 한도 초과 — 검색 결과를 직접 조회하세요."
    from app.agents.registry import agent_registry
    from app.agents.librarian.graph import build_librarian_chat_initial_state
    sub_config = _make_sub_config(config, "librarian")
    graph = agent_registry.get("librarian")
    if graph is None:
        return "Librarian 에이전트를 사용할 수 없습니다."
    initial_state = build_librarian_chat_initial_state(
        query=query,
        context=context,
        config=sub_config,
    )
    result = await graph.ainvoke(initial_state, config=sub_config)
    return result.get("final_response", "검색 결과 없음")


@tool
async def delegate_to_analyst(
    query: str,
    context: str = "",
    *,
    config: RunnableConfig,
) -> str:
    """Analyst 에이전트에게 패턴 분석을 위임합니다.

    Args:
        query: 분석 질문
        context: 추가 맥락 (선택)

    Returns:
        Analyst의 분석 결과 요약
    """
    if _get_delegation_depth(config) >= _MAX_DELEGATION_DEPTH:
        return "위임 깊이 한도 초과."
    from app.agents.registry import agent_registry
    from app.agents.analyst.graph import build_analyst_initial_state
    sub_config = _make_sub_config(config, "analyst")
    graph = agent_registry.get("analyst")
    if graph is None:
        return "Analyst 에이전트를 사용할 수 없습니다."
    initial_state = build_analyst_initial_state(
        query=query,
        context=context,
        config=sub_config,
    )
    result = await graph.ainvoke(initial_state, config=sub_config)
    return result.get("final_response", "분석 결과 없음")


@tool
async def delegate_to_curator(
    source_id: str,
    source_type: str,
    content: str,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Curator 에이전트에게 엔티티 추출 및 그래프 저장을 위임합니다.

    Args:
        source_id: 소스 ID
        source_type: "scrap" 또는 "diary"
        content: 처리할 텍스트

    Returns:
        entities_saved(int), relations_saved(int)
    """
    if _get_delegation_depth(config) >= _MAX_DELEGATION_DEPTH:
        return {"entities_saved": 0, "relations_saved": 0, "error": "위임 깊이 한도 초과"}
    from app.agents.tools.graph_tools import extract_entities, extract_relations, save_to_graph
    entities = await extract_entities.ainvoke({"text": content}, config=config)
    entity_names = [e["name"] for e in entities]
    relations = await extract_relations.ainvoke(
        {"text": content, "entities": entity_names}, config=config
    )
    result = await save_to_graph.ainvoke(
        {
            "source_id": source_id,
            "source_type": source_type,
            "entities": entities,
            "relations": relations,
        },
        config=config,
    )
    return result
```

**Step 3: 구문 검증 및 커밋**

```bash
cd backend && python -c "
import ast
for f in ['app/agents/tools/report_tools.py', 'app/agents/tools/delegation_tools.py']:
    ast.parse(open(f, encoding='utf-8').read())
print('All OK')
"
git add backend/app/agents/tools/
git commit -m "feat: report tools + delegation tools 완성 (S10-8)"
```

---

### Task 1.9: Tool Registry `__init__.py` 완성

**Files:**
- Modify: `backend/app/agents/tools/__init__.py`

**Step 1: `__init__.py`에 전체 export 작성**

```python
# backend/app/agents/tools/__init__.py
"""Memoir AI 에이전트 tool registry.

각 에이전트별 tool set:
- SOCRATES_TOOLS: 감성 코칭 에이전트 tools
- LIBRARIAN_TOOLS: 지식 검색 에이전트 tools
- ANALYST_TOOLS: 패턴 분석 에이전트 tools
- SCRIBE_TOOLS: 콘텐츠 처리 에이전트 tools
- CURATOR_TOOLS: 그래프 관리 에이전트 tools
- REPORTER_TOOLS: 보고서 에이전트 tools
- ALL_TOOLS: 전체 tools
"""
from app.agents.tools.retrieval_tools import (
    search_scraps,
    search_graph_entities,
    get_graph_context,
)
from app.agents.tools.diary_tools import (
    search_diaries,
    get_diary_detail,
    get_emotion_trend,
    list_diary_dates,
    get_diary_statistics,
)
from app.agents.tools.reflection_tools import (
    generate_reflection_questions,
    detect_cognitive_distortions,
    generate_diary_draft,
)
from app.agents.tools.content_tools import (
    classify_content,
    summarize_content,
    extract_tags,
    analyze_sentiment,
    inline_edit,
)
from app.agents.tools.graph_tools import (
    extract_entities,
    extract_relations,
    save_to_graph,
    get_ego_graph,
    get_hub_entities,
    get_orphan_entities,
    suggest_connections,
)
from app.agents.tools.analysis_tools import (
    get_community_insights,
    find_connections,
    compare_content,
    get_entity_timeline,
    get_content_timeline,
)
from app.agents.tools.session_tools import (
    search_past_conversations,
    get_user_profile,
)
from app.agents.tools.kb_tools import (
    get_scrap_detail,
    list_recent_scraps,
    list_scraps_by_tag,
    update_scrap_metadata,
)
from app.agents.tools.stats_tools import (
    get_knowledge_stats,
    get_topic_distribution,
    get_activity_streak,
)
from app.agents.tools.report_tools import (
    generate_daily_digest,
    generate_daily_insights,
    generate_weekly_report,
    generate_monthly_report,
)
from app.agents.tools.delegation_tools import (
    delegate_to_librarian,
    delegate_to_analyst,
    delegate_to_curator,
)

SOCRATES_TOOLS = [
    search_diaries,
    get_diary_detail,
    get_emotion_trend,
    search_past_conversations,
    generate_reflection_questions,
    detect_cognitive_distortions,
    generate_diary_draft,
    delegate_to_librarian,
    delegate_to_analyst,
]

LIBRARIAN_TOOLS = [
    search_scraps,
    search_graph_entities,
    get_graph_context,
    search_diaries,
    get_community_insights,
    search_past_conversations,
    get_scrap_detail,
    list_recent_scraps,
    list_scraps_by_tag,
    delegate_to_curator,
    delegate_to_analyst,
]

ANALYST_TOOLS = [
    search_graph_entities,
    get_graph_context,
    get_community_insights,
    find_connections,
    get_emotion_trend,
    search_scraps,
    get_ego_graph,
    get_hub_entities,
    get_entity_timeline,
    get_topic_distribution,
    get_content_timeline,
    compare_content,
    list_scraps_by_tag,
    get_knowledge_stats,
    delegate_to_librarian,
]

SCRIBE_TOOLS = [
    classify_content,
    summarize_content,
    extract_tags,
    analyze_sentiment,
    inline_edit,
    update_scrap_metadata,
    delegate_to_curator,
]

CURATOR_TOOLS = [
    extract_entities,
    extract_relations,
    save_to_graph,
    search_graph_entities,
    get_ego_graph,
    get_orphan_entities,
    get_hub_entities,
    suggest_connections,
    update_scrap_metadata,
]

REPORTER_TOOLS = [
    generate_daily_digest,
    generate_daily_insights,
    generate_weekly_report,
    generate_monthly_report,
    get_knowledge_stats,
    get_activity_streak,
    get_diary_statistics,
    list_recent_scraps,
    delegate_to_analyst,
    delegate_to_librarian,
]

ALL_TOOLS = list({
    id(t): t
    for t in (
        SOCRATES_TOOLS
        + LIBRARIAN_TOOLS
        + ANALYST_TOOLS
        + SCRIBE_TOOLS
        + CURATOR_TOOLS
        + REPORTER_TOOLS
    )
}.values())
```

**Step 2: 구문 검증**

```bash
cd backend && python -c "import ast; ast.parse(open('app/agents/tools/__init__.py', encoding='utf-8').read()); print('OK')"
```

**Step 3: 커밋**

```bash
git add backend/app/agents/tools/__init__.py
git commit -m "feat: tool registry __init__.py 완성 — 51개 tool export (S10-9)"
```

---

## Sprint 2: Socrates ReAct Agent

### Task 2.1: ReAct Agent Factory

**Files:**
- Create: `backend/app/agents/react_agent.py`

**Step 1: 파일 작성**

```python
# backend/app/agents/react_agent.py
"""ReAct 에이전트 생성 팩토리."""
from __future__ import annotations
from typing import Any
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent
from langgraph.graph.state import CompiledStateGraph


def build_react_agent(
    llm: BaseChatModel,
    tools: list[BaseTool],
    system_prompt: str,
    max_steps: int = 8,
) -> CompiledStateGraph:
    """ReAct 에이전트 그래프를 생성한다.

    Args:
        llm: tool calling을 지원하는 LLM
        tools: 에이전트가 사용할 tool 목록
        system_prompt: 에이전트 시스템 프롬프트
        max_steps: 최대 ReAct 루프 스텝 수 (기본 8)

    Returns:
        컴파일된 LangGraph StateGraph
    """
    return create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt,
        max_steps=max_steps,
    )
```

**Step 2: 구문 검증 및 커밋**

```bash
cd backend && python -c "import ast; ast.parse(open('app/agents/react_agent.py', encoding='utf-8').read()); print('OK')"
git add backend/app/agents/react_agent.py
git commit -m "feat: ReAct agent factory (S10-10)"
```

---

### Task 2.2: Socrates ReAct 그래프로 전환

**Files:**
- Modify: `backend/app/agents/socrates/graph.py`
- Create: `backend/app/agents/socrates/prompts_react.py`

**Step 1: Socrates ReAct 프롬프트 작성**

`backend/app/agents/socrates/prompts_react.py`:

```python
# backend/app/agents/socrates/prompts_react.py
"""Socrates ReAct 에이전트 시스템 프롬프트."""

SOCRATES_REACT_SYSTEM_PROMPT = """당신은 Socrates입니다 — 소크라테스식 대화와 감성 코칭을 전문으로 하는 AI 동반자입니다.

## 역할
- 감정 공감 → 깊은 탐구 → 인사이트 순서로 대화를 이끌어 갑니다
- 판단 없이 사용자의 생각과 감정을 탐색합니다
- 필요할 때 도구를 사용해 맥락을 보강합니다

## 도구 사용 원칙
1. 사용자가 과거 경험을 언급하면 → search_diaries로 관련 일기 검색
2. 감정 트렌드가 필요하면 → get_emotion_trend 호출
3. 이전 대화 맥락이 필요하면 → search_past_conversations 호출
4. 인지 왜곡이 감지되면 → detect_cognitive_distortions로 분석
5. 사용자가 메모/기사 내용을 묻는다면 → delegate_to_librarian으로 위임
6. 관심사/패턴을 묻는다면 → delegate_to_analyst로 위임

## 대화 스타일
- 한 번에 하나의 질문만
- 공감 먼저, 해결책은 나중에
- 200자 이하의 간결한 응답 (필요할 때만 길게)
- 사용자 언어(한국어/영어)를 그대로 사용

## 도구를 사용하지 않아도 되는 경우
- 단순 인사, 감사 표현
- 이미 충분한 맥락이 있는 경우
- 감정적 지지만 필요한 경우 (즉각 공감이 우선)
"""
```

**Step 2: `socrates/graph.py` 수정**

기존 파일 읽고, 다음 패턴으로 `build_socrates_graph()` 함수 추가 (기존 함수 유지, 새 함수 추가):

```python
# backend/app/agents/socrates/graph.py에 추가할 내용
from app.agents.react_agent import build_react_agent
from app.agents.tools import SOCRATES_TOOLS
from app.agents.socrates.prompts_react import SOCRATES_REACT_SYSTEM_PROMPT
from app.core.llm import get_llm


def build_socrates_react_graph():
    """Socrates ReAct 에이전트 그래프를 빌드한다."""
    llm = get_llm(mode="chat")
    return build_react_agent(
        llm=llm,
        tools=SOCRATES_TOOLS,
        system_prompt=SOCRATES_REACT_SYSTEM_PROMPT,
        max_steps=8,
    )
```

기존 `register_socrates_graph()` 수정:

```python
def register_socrates_graph(registry) -> None:
    """Socrates 에이전트를 레지스트리에 등록한다."""
    graph = build_socrates_react_graph()
    registry.register("socrates", graph)
```

**Step 3: 구문 검증 및 커밋**

```bash
cd backend && python -c "import ast; ast.parse(open('app/agents/socrates/graph.py', encoding='utf-8').read()); print('OK')"
git add backend/app/agents/socrates/
git commit -m "feat: Socrates ReAct 에이전트 전환 (S10-11)"
```

---

### Task 2.3: SocratesService astream_events 전환

**Files:**
- Modify: `backend/app/services/socrates_service.py`

**Step 1: 현재 파일 읽기 (반드시 먼저 읽을 것)**

```bash
cat backend/app/services/socrates_service.py
```

**Step 2: `send_message` 메서드 수정**

현재 `graph.astream()` 방식을 `graph.astream_events(version="v2")`로 교체.

핵심 변경 패턴:

```python
async def send_message(...) -> AsyncGenerator[str, None]:
    # ... 기존 초기화 코드 유지 ...

    # 변경: astream → astream_events
    async for event in graph.astream_events(
        initial_state,
        config=RunnableConfig(
            configurable={
                "user_id": user_id,
                "session_id": session_id,
            }
        ),
        version="v2",
    ):
        event_type = event.get("event", "")

        # 토큰 스트리밍
        if event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                token = chunk.content
                if isinstance(token, str):
                    yield f"data: {json.dumps({'content': token})}\n\n"
                elif isinstance(token, list):
                    for part in token:
                        if isinstance(part, dict) and part.get("type") == "text":
                            yield f"data: {json.dumps({'content': part['text']})}\n\n"

        # Tool 시작
        elif event_type == "on_tool_start":
            tool_name = event.get("name", "")
            tool_input = event.get("data", {}).get("input", {})
            yield f"data: {json.dumps({'step': tool_name, 'status': 'started', 'args': str(tool_input)[:100]})}\n\n"

        # Tool 완료
        elif event_type == "on_tool_end":
            tool_name = event.get("name", "")
            output = event.get("data", {}).get("output", "")
            yield f"data: {json.dumps({'step': tool_name, 'status': 'done', 'detail': str(output)[:200]})}\n\n"

        # 최종 출력 (references 수집)
        elif event_type == "on_chain_end":
            output = event.get("data", {}).get("output", {})
            if isinstance(output, dict) and "messages" in output:
                last_msg = output["messages"][-1] if output["messages"] else None
                if last_msg and hasattr(last_msg, "content"):
                    # references 추출 로직 (기존 유지)
                    pass

    yield f"data: {json.dumps({'done': True})}\n\n"
```

**Step 3: 구문 검증 및 커밋**

```bash
cd backend && python -c "import ast; ast.parse(open('app/services/socrates_service.py', encoding='utf-8').read()); print('OK')"
git add backend/app/services/socrates_service.py
git commit -m "feat: SocratesService astream_events 전환 + step SSE 이벤트 (S10-12)"
```

---

## Sprint 3: Frontend Thinking Process UI

### Task 3.1: SSE 타입 확장

**Files:**
- Modify: `frontend/src/types/socrates.ts`
- Create: `frontend/src/types/agentStep.ts`

**Step 1: `agentStep.ts` 생성**

```typescript
// frontend/src/types/agentStep.ts
export type AgentStepStatus = 'pending' | 'active' | 'done' | 'error';

export interface AgentStep {
  id: string;          // 고유 ID (tool name + timestamp)
  tool: string;        // tool 이름 (예: "search_diaries")
  label: string;       // 사용자 표시 레이블 (예: "일기 검색 중")
  status: AgentStepStatus;
  detail?: string;     // 완료 시 결과 요약
  startedAt: number;   // Date.now()
  endedAt?: number;
}

export const TOOL_LABELS: Record<string, string> = {
  search_diaries: '일기 검색',
  get_diary_detail: '일기 상세 조회',
  get_emotion_trend: '감정 추세 분석',
  search_past_conversations: '이전 대화 검색',
  generate_reflection_questions: '성찰 질문 생성',
  detect_cognitive_distortions: '인지 왜곡 분석',
  generate_diary_draft: '일기 초안 생성',
  search_scraps: '스크랩 검색',
  search_graph_entities: '그래프 엔티티 검색',
  get_graph_context: '그래프 컨텍스트 조회',
  get_community_insights: '커뮤니티 인사이트',
  delegate_to_librarian: 'Librarian에게 위임',
  delegate_to_analyst: 'Analyst에게 위임',
  delegate_to_curator: 'Curator에게 위임',
};

export function getToolLabel(toolName: string): string {
  return TOOL_LABELS[toolName] ?? toolName.replace(/_/g, ' ');
}
```

**Step 2: `socrates.ts` 타입 확장**

`SocratesStreamChunk`에 신규 필드 추가:
```typescript
export interface SocratesStreamChunk {
  content?: string;
  done?: boolean;
  error?: string;
  title?: string;
  references?: SocratesReference[];
  // 신규 필드
  step?: string;
  status?: 'started' | 'done';
  args?: string;
  detail?: string;
  agent?: string;
}
```

**Step 3: 타입 검증**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```
Expected: 0 errors

**Step 4: 커밋**

```bash
git add frontend/src/types/
git commit -m "feat: AgentStep 타입 + SocratesStreamChunk step 필드 추가 (S10-13)"
```

---

### Task 3.2: ThinkingProcess 컴포넌트

**Files:**
- Create: `frontend/src/components/socrates/ThinkingProcess.tsx`

**Step 1: 컴포넌트 작성**

```tsx
// frontend/src/components/socrates/ThinkingProcess.tsx
import React, { useState } from 'react';
import { AgentStep, AgentStepStatus, getToolLabel } from '../../types/agentStep';

interface ThinkingProcessProps {
  steps: AgentStep[];
  isThinking: boolean;
  className?: string;
}

function StepIcon({ status }: { status: AgentStepStatus }) {
  if (status === 'done') {
    return <span className="thinking-step-icon thinking-step-icon--done">✓</span>;
  }
  if (status === 'active') {
    return <span className="thinking-step-icon thinking-step-icon--active" />;
  }
  if (status === 'error') {
    return <span className="thinking-step-icon thinking-step-icon--error">✗</span>;
  }
  return <span className="thinking-step-icon thinking-step-icon--pending" />;
}

export function ThinkingProcess({
  steps,
  isThinking,
  className = '',
}: ThinkingProcessProps) {
  const [expanded, setExpanded] = useState(false);

  if (!isThinking && steps.length === 0) return null;

  const activeStep = steps.find((s) => s.status === 'active');
  const doneCount = steps.filter((s) => s.status === 'done').length;

  return (
    <div className={`thinking-process ${className}`}>
      <button
        className="thinking-process__header"
        onClick={() => setExpanded((v) => !v)}
        type="button"
      >
        <span className="thinking-process__spinner" aria-hidden={!isThinking} />
        <span className="thinking-process__title">
          {isThinking
            ? activeStep
              ? `${getToolLabel(activeStep.tool)} 중...`
              : '생각하고 있습니다...'
            : `${doneCount}개 단계 완료`}
        </span>
        <span className="thinking-process__toggle">
          {expanded ? '▲' : '▼'}
        </span>
      </button>

      {expanded && steps.length > 0 && (
        <ul className="thinking-process__steps">
          {steps.map((step) => (
            <li key={step.id} className={`thinking-step thinking-step--${step.status}`}>
              <StepIcon status={step.status} />
              <span className="thinking-step__label">
                {getToolLabel(step.tool)}
              </span>
              {step.detail && step.status === 'done' && (
                <span className="thinking-step__detail">{step.detail}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

**Step 2: TypeScript 검증**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

**Step 3: 커밋**

```bash
git add frontend/src/components/socrates/ThinkingProcess.tsx
git commit -m "feat: ThinkingProcess 컴포넌트 (에이전트 thinking 실시간 표시) (S10-14)"
```

---

### Task 3.3: useSocratesChat hook agentSteps 추가

**Files:**
- Modify: `frontend/src/hooks/useSocratesChat.ts`

**Step 1: 현재 파일 읽기**

```bash
cat frontend/src/hooks/useSocratesChat.ts
```

**Step 2: agentSteps state 추가 및 SSE 처리 확장**

핵심 변경 패턴:
```typescript
// 추가할 state
const [agentSteps, setAgentSteps] = useState<AgentStep[]>([]);

// SSE 청크 처리에 추가
if (chunk.step && chunk.status === 'started') {
  setAgentSteps(prev => [...prev, {
    id: `${chunk.step}-${Date.now()}`,
    tool: chunk.step,
    label: getToolLabel(chunk.step),
    status: 'active',
    startedAt: Date.now(),
  }]);
}
if (chunk.step && chunk.status === 'done') {
  setAgentSteps(prev => prev.map(s =>
    s.tool === chunk.step && s.status === 'active'
      ? { ...s, status: 'done', detail: chunk.detail, endedAt: Date.now() }
      : s
  ));
}

// 메시지 시작 시 초기화
setAgentSteps([]);
```

**Step 3: hook이 agentSteps를 반환하도록 추가**

```typescript
return {
  // ... 기존 반환값 ...
  agentSteps,
  isThinking: isStreaming && agentSteps.some(s => s.status === 'active'),
};
```

**Step 4: TypeScript 검증 및 커밋**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
git add frontend/src/hooks/useSocratesChat.ts
git commit -m "feat: useSocratesChat에 agentSteps state 추가 (S10-15)"
```

---

### Task 3.4: SocratesMessageList ThinkingProcess 교체

**Files:**
- Modify: `frontend/src/components/socrates/SocratesMessageList.tsx`
- Modify: `frontend/src/components/SocratesView.css` (또는 관련 CSS 파일)

**Step 1: bouncing dots를 ThinkingProcess로 교체**

`SocratesMessageList.tsx`에서 `isStreaming && !lastToken` 조건의 bouncing dots 렌더링을 `ThinkingProcess` 컴포넌트로 교체:

```tsx
import { ThinkingProcess } from './ThinkingProcess';

// 기존 bouncing dots 대신:
{isThinking && (
  <ThinkingProcess
    steps={agentSteps}
    isThinking={isThinking}
    className="message-thinking"
  />
)}
```

**Step 2: CSS 추가**

```css
/* ThinkingProcess 관련 CSS */
.thinking-process {
  background: var(--surface-2, #f5f5f5);
  border-radius: 8px;
  padding: 8px 12px;
  margin: 4px 0;
  max-width: 480px;
  font-size: 0.85rem;
}

.thinking-process__header {
  display: flex;
  align-items: center;
  gap: 8px;
  background: none;
  border: none;
  cursor: pointer;
  width: 100%;
  text-align: left;
  padding: 0;
  color: var(--text-secondary, #666);
}

.thinking-process__spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #ccc;
  border-top-color: var(--accent, #7c5cbf);
  border-radius: 50%;
  animation: thinking-spin 0.8s linear infinite;
  flex-shrink: 0;
}

.thinking-process__spinner[aria-hidden="true"] {
  display: none;
}

@keyframes thinking-spin {
  to { transform: rotate(360deg); }
}

.thinking-process__title {
  flex: 1;
  font-weight: 500;
}

.thinking-process__toggle {
  font-size: 0.7rem;
  opacity: 0.6;
}

.thinking-process__steps {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.thinking-step {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
}

.thinking-step-icon {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  flex-shrink: 0;
}

.thinking-step-icon--done {
  background: #4caf50;
  color: white;
}

.thinking-step-icon--active {
  border: 2px solid var(--accent, #7c5cbf);
  border-top-color: transparent;
  animation: thinking-spin 0.8s linear infinite;
}

.thinking-step-icon--pending {
  border: 2px solid #ccc;
}

.thinking-step-icon--error {
  background: #f44336;
  color: white;
}

.thinking-step__label {
  font-size: 0.82rem;
  color: var(--text-primary, #333);
}

.thinking-step__detail {
  font-size: 0.75rem;
  color: var(--text-secondary, #888);
  margin-left: auto;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

**Step 3: TypeScript + 빌드 검증**

```bash
cd frontend && npx tsc --noEmit && npm run build 2>&1 | tail -20
```
Expected: 빌드 성공

**Step 4: 커밋**

```bash
git add frontend/src/
git commit -m "feat: SocratesMessageList ThinkingProcess UI 교체 + CSS (S10-16)"
```

---

## Sprint 4: Librarian + Analyst ReAct Agents

### Task 4.1: Librarian Chat ReAct 전환

**Files:**
- Modify: `backend/app/agents/librarian/graph.py`
- Create: `backend/app/agents/librarian/prompts_react.py`

**Step 1: `prompts_react.py` 작성**

```python
# backend/app/agents/librarian/prompts_react.py
"""Librarian ReAct 에이전트 시스템 프롬프트."""

LIBRARIAN_REACT_SYSTEM_PROMPT = """당신은 Librarian입니다 — 사용자의 지식 베이스를 탐색하고 정확한 정보를 제공하는 AI 사서입니다.

## 역할
- 저장된 스크랩, 일기, 그래프에서 관련 정보를 검색합니다
- 출처를 명시하여 팩트 기반으로 답변합니다
- 모순된 정보를 발견하면 사용자에게 알립니다

## 도구 사용 전략
1. 먼저 search_scraps로 관련 스크랩 검색
2. 그래프 연결이 필요하면 search_graph_entities + get_graph_context
3. 패턴 분석이 필요하면 delegate_to_analyst
4. 일기 관련이면 search_diaries

## 응답 원칙
- 반드시 출처(스크랩 제목, 날짜)를 언급
- "저장하신 내용에 따르면..." 형식 사용
- 정보가 없으면 솔직하게 "저장된 내용이 없습니다" 고지
- 한국어/영어 입력 언어 그대로 답변
"""
```

**Step 2: `librarian/graph.py` 수정 (chat graph 부분)**

기존 `create_librarian_chat_graph()` 또는 chat 등록 함수를 ReAct로 교체:

```python
def build_librarian_chat_react_graph():
    """Librarian 채팅 ReAct 에이전트 그래프를 빌드한다."""
    from app.agents.react_agent import build_react_agent
    from app.agents.tools import LIBRARIAN_TOOLS
    from app.agents.librarian.prompts_react import LIBRARIAN_REACT_SYSTEM_PROMPT
    from app.core.llm import get_llm
    llm = get_llm(mode="chat")
    return build_react_agent(
        llm=llm,
        tools=LIBRARIAN_TOOLS,
        system_prompt=LIBRARIAN_REACT_SYSTEM_PROMPT,
        max_steps=8,
    )


def build_librarian_chat_initial_state(
    query: str,
    context: str,
    config,
) -> dict:
    """Librarian 채팅 초기 상태를 생성한다."""
    from langchain_core.messages import HumanMessage
    return {
        "messages": [HumanMessage(content=query if not context else f"{context}\n\n{query}")],
    }
```

**Step 3: 구문 검증 및 커밋**

```bash
cd backend && python -c "import ast; ast.parse(open('app/agents/librarian/graph.py', encoding='utf-8').read()); print('OK')"
git add backend/app/agents/librarian/
git commit -m "feat: Librarian ReAct 채팅 에이전트 전환 (S10-17)"
```

---

### Task 4.2: Analyst 에이전트 신규 생성

**Files:**
- Create: `backend/app/agents/analyst/__init__.py`
- Create: `backend/app/agents/analyst/graph.py`
- Create: `backend/app/agents/analyst/prompts.py`

**Step 1: `prompts.py` 작성**

```python
# backend/app/agents/analyst/prompts.py
"""Analyst ReAct 에이전트 시스템 프롬프트."""

ANALYST_REACT_SYSTEM_PROMPT = """당신은 Analyst입니다 — 사용자의 지식 패턴과 연결을 발견하는 AI 분석가입니다.

## 역할
- 지식 그래프에서 숨겨진 연결과 패턴을 발견합니다
- 감정 추세와 관심사 분포를 분석합니다
- 데이터 기반의 인사이트를 생성합니다

## 도구 사용 전략
1. 패턴 발견: get_community_insights → find_connections
2. 트렌드: get_emotion_trend + get_entity_timeline
3. 허브 분석: get_hub_entities + get_ego_graph
4. 주제 분포: get_topic_distribution + list_scraps_by_tag
5. 상세 검색 필요 시: delegate_to_librarian

## 응답 원칙
- 구체적인 수치와 예시 포함
- "패턴이 보입니다...", "연결이 발견됩니다..." 형식
- 인사이트를 actionable하게 제시
"""
```

**Step 2: `graph.py` 작성**

```python
# backend/app/agents/analyst/graph.py
"""Analyst ReAct 에이전트 그래프."""
from __future__ import annotations


def build_analyst_react_graph():
    """Analyst ReAct 에이전트 그래프를 빌드한다."""
    from app.agents.react_agent import build_react_agent
    from app.agents.tools import ANALYST_TOOLS
    from app.agents.analyst.prompts import ANALYST_REACT_SYSTEM_PROMPT
    from app.core.llm import get_llm
    llm = get_llm(mode="chat")
    return build_react_agent(
        llm=llm,
        tools=ANALYST_TOOLS,
        system_prompt=ANALYST_REACT_SYSTEM_PROMPT,
        max_steps=10,
    )


def build_analyst_initial_state(
    query: str,
    context: str = "",
    config=None,
) -> dict:
    """Analyst 초기 상태를 생성한다."""
    from langchain_core.messages import HumanMessage
    content = f"{context}\n\n{query}" if context else query
    return {"messages": [HumanMessage(content=content)]}


def register_analyst_graph(registry) -> None:
    """Analyst 에이전트를 레지스트리에 등록한다."""
    graph = build_analyst_react_graph()
    registry.register("analyst", graph)
```

**Step 3: 구문 검증 및 커밋**

```bash
cd backend && python -c "
import ast
for f in ['app/agents/analyst/graph.py', 'app/agents/analyst/prompts.py']:
    ast.parse(open(f, encoding='utf-8').read())
print('All OK')
"
git add backend/app/agents/analyst/
git commit -m "feat: Analyst 에이전트 신규 생성 (S10-18)"
```

---

## Sprint 5: Supervisor + Registry 업데이트

### Task 5.1: Supervisor Agent 생성

**Files:**
- Create: `backend/app/agents/supervisor/__init__.py`
- Create: `backend/app/agents/supervisor/prompts.py`
- Create: `backend/app/agents/supervisor/graph.py`

**Step 1: `prompts.py` 작성**

```python
# backend/app/agents/supervisor/prompts.py
"""Supervisor 라우팅 에이전트 프롬프트."""

SUPERVISOR_SYSTEM_PROMPT = """당신은 Memoir AI의 Supervisor입니다. 사용자의 쿼리를 분석하여 적절한 전문 에이전트에게 라우팅하거나 직접 응답합니다.

## 라우팅 규칙
- **Socrates로 라우팅**: 감정, 회고, 일기, 고민, 기분 관련 ("기분이 안 좋아", "요즘 힘들어", "지난 주 돌아보면")
- **Librarian으로 라우팅**: 저장한 내용 검색, 특정 정보 조회 ("React에 대해 저장한 거", "스크랩 찾아줘")
- **Analyst로 라우팅**: 패턴, 트렌드, 관심사 분석 ("내가 자주 보는 주제", "어떤 패턴이")
- **직접 응답**: 단순 인사, 잡담, 시스템 문의 ("안녕", "고마워", "어떻게 사용해")

## 도구
route_to_socrates, route_to_librarian, route_to_analyst, respond_directly 중 하나 선택.

반드시 도구를 사용하여 응답하세요. 절대 텍스트로만 응답하지 마세요.
"""
```

**Step 2: `graph.py` 작성**

```python
# backend/app/agents/supervisor/graph.py
"""Supervisor 라우팅 에이전트."""
from __future__ import annotations
from typing import Any
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from app.agents.supervisor.prompts import SUPERVISOR_SYSTEM_PROMPT


@tool
def route_to_socrates(reason: str) -> str:
    """감성 코칭 에이전트(Socrates)로 라우팅합니다."""
    return f"ROUTE:socrates:{reason}"


@tool
def route_to_librarian(reason: str) -> str:
    """지식 검색 에이전트(Librarian)로 라우팅합니다."""
    return f"ROUTE:librarian:{reason}"


@tool
def route_to_analyst(reason: str) -> str:
    """패턴 분석 에이전트(Analyst)로 라우팅합니다."""
    return f"ROUTE:analyst:{reason}"


@tool
def respond_directly(response: str) -> str:
    """직접 응답합니다 (단순 인사/잡담)."""
    return f"DIRECT:{response}"


SUPERVISOR_TOOLS = [
    route_to_socrates,
    route_to_librarian,
    route_to_analyst,
    respond_directly,
]


def build_supervisor_graph():
    """Supervisor 에이전트 그래프를 빌드한다."""
    from app.core.llm import get_llm
    llm = get_llm(mode="chat")
    return create_react_agent(
        model=llm,
        tools=SUPERVISOR_TOOLS,
        prompt=SUPERVISOR_SYSTEM_PROMPT,
        max_steps=2,  # 라우팅은 빠르게
    )


def parse_supervisor_result(result: dict) -> tuple[str, str]:
    """Supervisor 결과에서 (target_agent, reason/response) 추출한다."""
    messages = result.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, "content") and isinstance(msg.content, str):
            content = msg.content
            if content.startswith("ROUTE:"):
                parts = content.split(":", 2)
                if len(parts) >= 3:
                    return parts[1], parts[2]
            elif content.startswith("DIRECT:"):
                return "direct", content[7:]
    return "socrates", "기본 라우팅"


def register_supervisor_graph(registry) -> None:
    """Supervisor 에이전트를 레지스트리에 등록한다."""
    graph = build_supervisor_graph()
    registry.register("supervisor", graph)
```

**Step 3: 구문 검증 및 커밋**

```bash
cd backend && python -c "
import ast
for f in ['app/agents/supervisor/graph.py', 'app/agents/supervisor/prompts.py']:
    ast.parse(open(f, encoding='utf-8').read())
print('All OK')
"
git add backend/app/agents/supervisor/
git commit -m "feat: Supervisor 라우팅 에이전트 생성 (S10-19)"
```

---

### Task 5.2: AgentRegistry에 새 에이전트 등록

**Files:**
- Modify: `backend/app/agents/registry.py`

**Step 1: 현재 파일 읽기**

```bash
cat backend/app/agents/registry.py
```

**Step 2: 파일 수정 — Analyst, Supervisor 등록 추가**

기존 `register_all_agents()` 함수 또는 초기화 코드에 추가:

```python
# Analyst 등록
from app.agents.analyst.graph import register_analyst_graph
register_analyst_graph(registry)

# Supervisor 등록
from app.agents.supervisor.graph import register_supervisor_graph
register_supervisor_graph(registry)
```

기존 oracle fallback을 socrates로 변경:
```python
def get(self, agent_type: str):
    graph = self._registry.get(agent_type)
    if graph is None:
        graph = self._registry.get("socrates")  # oracle → socrates
    return graph
```

**Step 3: 구문 검증 및 커밋**

```bash
cd backend && python -c "import ast; ast.parse(open('app/agents/registry.py', encoding='utf-8').read()); print('OK')"
git add backend/app/agents/registry.py
git commit -m "feat: AgentRegistry에 Analyst + Supervisor 등록 (S10-20)"
```

---

## Sprint 6: Scribe + Curator + Reporter Agents

### Task 6.1: Scribe 에이전트 생성

**Files:**
- Create: `backend/app/agents/scribe/__init__.py`
- Create: `backend/app/agents/scribe/prompts.py`
- Create: `backend/app/agents/scribe/graph.py`

**핵심 구현 패턴 (Task 4.2와 동일):**

`prompts.py`:
```python
SCRIBE_REACT_SYSTEM_PROMPT = """당신은 Scribe입니다 — 콘텐츠 분류, 요약, 태깅, 감정 분석 전문 AI입니다.

## 워크플로우
1. classify_content → SPAM이면 중단
2. summarize_content + extract_tags 병렬 처리
3. analyze_sentiment (일기인 경우)
4. delegate_to_curator (엔티티 추출 위임)
5. update_scrap_metadata (결과 저장)
"""
```

`graph.py`에서 `SCRIBE_TOOLS` 사용, `register_scribe_graph()` 함수 제공.

**커밋:**
```bash
git add backend/app/agents/scribe/
git commit -m "feat: Scribe 에이전트 생성 (콘텐츠 처리) (S10-21)"
```

---

### Task 6.2: Curator 에이전트 생성

**Files:**
- Create: `backend/app/agents/curator/__init__.py`
- Create: `backend/app/agents/curator/prompts.py`
- Create: `backend/app/agents/curator/graph.py`

`graph.py`에서 `CURATOR_TOOLS` 사용, `register_curator_graph()` 함수 제공.

**커밋:**
```bash
git add backend/app/agents/curator/
git commit -m "feat: Curator 에이전트 생성 (그래프 관리) (S10-22)"
```

---

### Task 6.3: Reporter 에이전트 생성

**Files:**
- Create: `backend/app/agents/reporter/__init__.py`
- Create: `backend/app/agents/reporter/prompts.py`
- Create: `backend/app/agents/reporter/graph.py`

`graph.py`에서 `REPORTER_TOOLS` 사용, `register_reporter_graph()` 함수 제공.

**커밋:**
```bash
git add backend/app/agents/reporter/
git commit -m "feat: Reporter 에이전트 생성 (보고서/디제스트) (S10-23)"
```

---

## Sprint 7-10: 후속 작업

### Sprint 7: GraphRAG 강화

**Task 7.1: mindmap_repository.py multi-hop 구현**

```python
# get_related_context() 수정
# 현재: depth=1 하드코딩
# 변경: variable-length path
cypher = f"""
MATCH path = (start:Entity {{name: $topic, user_id: $user_id}})-[:ENTITY_REL*1..{depth}]->(related:Entity)
WHERE related.name <> $topic
  AND ($type IS NULL OR related.type = $type)
WITH related, min(length(path)) AS distance,
     [r IN relationships(path) | r.rel_type] AS rel_types
RETURN DISTINCT related.name, related.type, rel_types, distance
ORDER BY distance LIMIT $limit
"""
```

**Task 7.2: ENTITY_REL user_id 격리**

```sql
-- KuzuDB migration
ALTER TABLE ENTITY_REL ADD user_id STRING DEFAULT '';
```

커밋: `feat: GraphRAG multi-hop + user isolation (S10-24~25)`

---

### Sprint 8: 화면별 Agent 연동

**Task 8.1: diary_router.py Scribe/Socrates tool 연동**

- `POST /diaries` → Scribe.analyze_sentiment + extract_tags
- `POST /diaries/review-questions` → Socrates.generate_reflection_questions
- `POST /diaries/generate-draft` → Socrates.generate_diary_draft

**Task 8.2: mindmap_router.py Analyst 연동**

- `GET /mindmap/insights` → Analyst agent 호출

커밋: `feat: Diary/Mindmap 라우터 에이전트 tool 연동 (S10-26~27)`

---

### Sprint 9: Legacy 파일 정리 + 검증

**삭제 대상:**
- `backend/app/agents/oracle/` (Supervisor 대체)
- `backend/app/agents/socrates/nodes/enrichment.py` (미사용)
- `backend/app/agents/socrates/nodes/context_assembly.py` (미사용)
- `backend/app/agents/socrates/context.py` (AgentContext와 중복)
- `backend/app/agents/graph_factory.py` (ReAct 대체)
- `backend/app/agents/state.py` (각 에이전트 자체 state 사용)

**최종 검증:**
```bash
cd backend && python -c "import ast; [ast.parse(open(f, encoding='utf-8').read()) for f in import glob; glob.glob('app/**/*.py', recursive=True)]"
cd frontend && npx tsc --noEmit && npm run build
```

커밋: `feat: legacy 파일 삭제 + 전체 검증 통과 (S10-28)`

---

### Sprint 10: MCP Server + 최종 E2E

**Task 10.1: MCP 서버 구현**

```python
# backend/app/mcp_server.py
from mcp.server.fastmcp import FastMCP
from app.agents.tools import ALL_TOOLS

mcp = FastMCP("Memoir AI Knowledge Base")

for tool_fn in ALL_TOOLS:
    mcp.add_tool(tool_fn)
```

**최종 E2E 검증 시나리오:**
1. "오늘 기분이 안 좋아" → Supervisor→Socrates → thinking UI 표시
2. "React에 대해 저장한 거 있어?" → Supervisor→Librarian → 출처 인용
3. "내가 자주 관심 갖는 주제는?" → Supervisor→Analyst → 인사이트 표시
4. 일기 저장 → Scribe(sentiment+tags) → Curator(entity extraction)
5. 마인드맵 → Analyst(cluster+trend)

커밋: `feat: MCP 서버 + 전체 E2E 검증 완료 (S10-29)`

---

## 참고: 기존 서비스 메서드 확인 필요 목록

Tool을 실제로 구현할 때 아래 기존 Repository/Service 메서드가 존재하는지 확인 후,
없으면 신규 추가가 필요합니다:

| Tool | Repository 메서드 | 존재 여부 확인 |
|------|-----------------|-------------|
| `search_diaries` | `DiaryRepository.search_diaries()` | 확인 필요 |
| `get_emotion_trend` | `DiaryRepository.get_emotion_trend()` | 확인 필요 |
| `get_diary_statistics` | `DiaryRepository.get_diary_statistics()` | 확인 필요 |
| `get_activity_streak` | `DiaryRepository.get_activity_streak()` | 확인 필요 |
| `list_diary_dates` | `DiaryRepository.list_diary_dates()` | 확인 필요 |
| `find_connections_between` | `MindmapRepository.find_connections_between()` | **없을 가능성 높음** |
| `get_entity_timeline` | `MindmapRepository.get_entity_timeline()` | **없을 가능성 높음** |
| `get_ego_graph` | `MindmapRepository.get_ego_graph()` | 확인 필요 |
| `get_hub_entities` | `MindmapRepository.get_hub_entities()` | 확인 필요 |
| `search_sessions_by_context` | `SocratesRepository.search_sessions_by_context()` | 확인 필요 |
| `scrap_repo.count()` | `ScrapRepository.count()` | 확인 필요 |
| `scrap_repo.list_recent()` | `ScrapRepository.list_recent()` | 확인 필요 |
| `get_content_timeline` | `HybridSearchService.get_content_timeline()` | **없을 가능성 높음** |

→ 각 Sprint Task 실행 전, 메서드 존재 여부 확인 후 없으면 Repository에 추가
