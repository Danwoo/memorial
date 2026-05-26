# ADR-002: Repository Protocol을 통한 의존성 역전

**Status**: Accepted
**Date**: 2026-04

## 컨텍스트

리팩토링 전: Service가 구체 Repository 클래스를 직접 import + 생성자에 type hint.
```python
class DigestService:
    def __init__(self, scrap_repo: ScrapRepository, ...):  # 구체 의존
```

문제:
- 테스트에서 `ScrapRepository`를 instantiate하려면 Supabase 클라이언트 필요 → 단위 테스트 불가
- 구현체 교체 어려움 (Supabase → 다른 백엔드)
- Repository와 Service가 양방향 결합

## 고려한 대안

| 옵션 | 의견 |
|------|------|
| **ABC (abstract base class) 상속** | "is-a" 강제. Python답지 않음 — 다중 상속 충돌, 명시적 inherits 부담 |
| **Duck typing (현 상태 유지)** | 타입 힌트 없음 → mypy 약함, 의도 불명확 |
| **`typing.Protocol` (선택)** | 구조적 typing — "has-a" 검증, 명시적 상속 0, runtime_checkable로 isinstance 가능 |

## 결정

**`typing.Protocol` + `@runtime_checkable`** 채택.

```python
# app/repositories/protocols/chat_repository_protocol.py
@runtime_checkable
class ChatRepositoryProtocol(Protocol):
    async def create_session(self, user_id: UUID, ...) -> ChatSession: ...
    # ...

# Service는 Protocol에만 의존
class ChatService:
    def __init__(self, chat_repo: ChatRepositoryProtocol):
        ...

# DI factory는 구체 클래스 인스턴스화
def get_chat_service(
    chat_repo: ChatRepository = Depends(get_chat_repository),
) -> ChatService:
    return ChatService(chat_repo)  # 구체 → Protocol로 ok (구조적 호환)
```

도입된 Protocol: Chat / Diary / Scrap / Mindmap / Calendar / Vector (6개).

## 트레이드오프

### 1. Protocol에 property가 있을 때 `runtime_checkable` 동작

- `MindmapRepositoryProtocol.is_connected`가 `@property`인데 Protocol의 runtime check가
  property를 확인하지 않음 (Python 3.11 기준).
- **답변**: 컴파일 타임 mypy 체크는 정상 동작. runtime `isinstance()`는
  duck typing fallback. 실제 코드에서 `isinstance(repo, MindmapRepositoryProtocol)`
  검증을 안 함 — 타입 힌트로만 활용.

### 2. 구체 import는 여전히 어딘가에 남아 있음

- `app/config/dependencies.py`와 `app/agents/container.py`는 구체 Repository를
  인스턴스화. 의존성 역전이 100% 완성 아님.
- **답변**: 의존성 역전 원칙은 **상위 모듈이 하위 모듈에 의존하지 않는다**가 핵심.
  DI factory는 **구성(composition root)** 으로서 구체를 알아도 됨 — 다른 layer는 Protocol만.
  이는 표준 패턴 (Mark Seemann, "Dependency Injection in .NET").

### 3. Protocol 시그니처 ↔ 구현체 drift 위험

- Protocol에 정의한 메서드 시그니처가 구현체와 어긋나도 컴파일 에러 안 남.
- **답변**: mypy strict 모드에서 검증 가능. 현재는 ruff만 적용. 다음 단계 mypy 추가 검토.
