"""엔티티 이름 canonicalization — 동의어 병합으로 그래프 중복 방지.

LLM이 prompt rule을 따르더라도 (예: "React 권장, ReactJS/리액트 회피"),
실제 추출 결과는 신뢰도가 100%가 아니다. 이 모듈은 보강 layer로:

- 정확 일치 alias map: "리액트" → "React"
- 케이스 무시: "React" / "react" / "REACT" 동일

추가는 자유롭게 가능. 운영 데이터에서 발견되는 변형을 발견할 때마다 추가.
"""

from __future__ import annotations

# 정확 일치 (case-sensitive) — 한국어/약어/표기 변형
_EXACT_ALIASES: dict[str, str] = {
    # JavaScript 생태계
    "리액트": "React",
    "ReactJS": "React",
    "React.js": "React",
    "Reactjs": "React",
    "자바스크립트": "JavaScript",
    "JS": "JavaScript",
    "Js": "JavaScript",
    "타입스크립트": "TypeScript",
    "TS": "TypeScript",
    "Ts": "TypeScript",
    "노드": "Node.js",
    "Node": "Node.js",
    "NodeJS": "Node.js",
    "NextJS": "Next.js",
    "Next": "Next.js",
    "React Native": "React Native",  # canonical 자체
    # Python 생태계
    "파이썬": "Python",
    "Py": "Python",
    "장고": "Django",
    "플라스크": "Flask",
    "FastAPI": "FastAPI",  # canonical
    # AI/ML
    "랭체인": "LangChain",
    "Langchain": "LangChain",
    "langchain": "LangChain",
    "LangGraph": "LangGraph",  # canonical
    "Langgraph": "LangGraph",
    "오픈AI": "OpenAI",
    "Openai": "OpenAI",
    "OPENAI": "OpenAI",
    "앤트로픽": "Anthropic",
    "구글": "Google",
    "MS": "Microsoft",
    # DB / Infra
    "Postgres": "PostgreSQL",
    "postgres": "PostgreSQL",
    "수파베이스": "Supabase",
    "supabase": "Supabase",
    "쿠즈DB": "KuzuDB",
    "KuzuDB": "KuzuDB",  # canonical
    "kuzu": "KuzuDB",
    "벡터DB": "Vector Database",
    "벡터 DB": "Vector Database",
    "Vector DB": "Vector Database",
}

# 대소문자 정규화는 별도 — "react" / "React" / "REACT" 등을 일관 처리
# (단, 약어 충돌 위험으로 화이트리스트만 적용)
_CASE_INSENSITIVE_CANONICAL: dict[str, str] = {
    name.lower(): name for name in {
        "React", "JavaScript", "TypeScript", "Python", "Node.js", "Next.js",
        "Django", "Flask", "FastAPI", "LangChain", "LangGraph",
        "OpenAI", "Anthropic", "Google", "Microsoft",
        "PostgreSQL", "Supabase", "KuzuDB", "Vector Database",
        "Docker", "Kubernetes", "Redis", "GraphQL",
    }
}


def canonicalize_entity_name(name: str) -> str:
    """엔티티 이름을 canonical form으로 정규화.

    1. 정확 일치(한국어/약어/표기 변형)면 그 결과
    2. 대소문자 무시 화이트리스트 일치 시 정식 표기
    3. 그 외는 원본 반환 (LLM이 추출한 이름 그대로)
    """
    stripped = name.strip()
    if not stripped:
        return stripped

    # 1. 정확 일치
    if stripped in _EXACT_ALIASES:
        return _EXACT_ALIASES[stripped]

    # 2. 대소문자 무시 일치
    lower = stripped.lower()
    if lower in _CASE_INSENSITIVE_CANONICAL:
        return _CASE_INSENSITIVE_CANONICAL[lower]

    return stripped
