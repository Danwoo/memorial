# ADR-005: OpenRouter primary + Gemini fallback

**Status**: Accepted (프로토타입 단계)
**Date**: 2026-02
**Re-evaluation trigger**: 일 LLM 호출 1000회 초과 또는 SLA 약속이 필요해질 때

## 컨텍스트

LLM 호출이 필요한 경로:
- 채팅 (Socrates/Oracle/Librarian 에이전트) — 스트리밍
- 다이어리 감정 분석 + 태그 추출
- 인지왜곡 분석 (CBT)
- 엔티티/관계 추출
- 다이제스트 질문 생성
- 세션 요약 + 자동 제목 생성

비용 + 안정성을 둘 다 챙겨야 한다.

## 고려한 대안

| 옵션 | 월 예상 비용 | Pros | Cons |
|------|------|------|------|
| **OpenAI 직접 (gpt-4o-mini)** | ~$15+ | 안정적, 한국어 OK | 비용 (프로토타입 단계에서 부담) |
| **Anthropic Claude 직접 (haiku)** | ~$20+ | 한국어 최상위 품질 | 비용 |
| **OpenRouter (upstage/solar-pro-3:free) — 선택** | $0 (rate limit) | 한국어 특화, 무료 | rate limit, 가용성 불확실 |
| **로컬 LLM (Ollama + qwen)** | $0 + EC2 비용 | 완전 통제 | 1GB RAM에서 비현실적 모델 크기 |
| **Gemini Flash** | $0~minimal | 안정, 한국어 OK | OpenRouter free tier에서는 모델 제한 |

## 결정

**Primary: OpenRouter (`upstage/solar-pro-3:free`)** — 한국어 특화 모델 무료 활용.
**Fallback: Gemini (`langchain_google_genai`)** — OpenRouter 장애/rate limit 시 자동 전환.

```python
# app/config/llm.py
def _make_llm(temperature, streaming, label):
    primary = ChatOpenAI(
        model="upstage/solar-pro-3:free",
        api_key=settings.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        ...
    )
    if settings.GOOGLE_API_KEY:
        return primary.with_fallbacks([_make_gemini_llm(...)])
    return primary
```

`with_fallbacks`는 LangChain Runnable의 primitive — primary 실패 시 자동으로 fallback 호출.

## 트레이드오프 (정직)

### 1. 무료 티어 의존 — 운영 SLA 없음

- OpenRouter free tier는 rate limit + 가용성 보장 없음.
- **대응**: **이 프로젝트는 프로토타입 단계**. 실 사용자 0~수십 명. SLA 필요 없음.
  운영 트래픽이 늘면 즉시 OpenAI/Claude 유료 모델로 전환 가능 — `_USE_OPENROUTER = False`
  한 줄 변경. 인터페이스 위에서 흡수됨.

### 2. 모델 품질 변동

- `upstage/solar-pro-3:free`는 한국어 특화지만 GPT-4 수준은 아님.
- **대응**: 분석/추출 작업(structured output)은 `with_structured_output(Schema)` +
  few-shot으로 형식 강제 → 모델 품질 영향 최소화 ([ADR 없음 — `graph_schemas.py` 참고]).
  대화형 작업(소크라테스식 질문)은 한국어 자연스러움이 더 중요 — solar가 강점.

### 3. Fallback 동작 추적 어려움

- LangChain `with_fallbacks`가 primary 실패를 silent하게 처리.
- **대응**: `TokenUsageLogger` callback이 양쪽에 모두 등록되어 로그에 label로 구분
  가능 (`creative` / `analytical` / `tagger` / `streaming`). 운영 시 fallback hit률
  메트릭으로 노출 검토.

### 4. Token 비용 추적 자동화 0

- 무료 티어라 현재 비용 추적 불필요.
- **대응**: `TokenUsageLogger`가 input/output/total tokens INFO 로깅. 유료 전환 시
  log aggregation(CloudWatch/Datadog) + 비용 환산 dashboard 추가하면 됨.

## 재평가 트리거

- 일 LLM 호출 1000회 초과 → 유료 전환 + SLA 보장
- 사용자 보고 "응답 품질 저하" → 모델 업그레이드 검토
- OpenRouter 정책 변경 (free tier 제거 등)
