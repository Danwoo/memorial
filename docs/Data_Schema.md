# Memoir AI - 데이터 스키마 (Data Schema)

## 1. 데이터 모델링 전략
Memoir AI는 데이터의 성격에 따라 두 저장소를 최적으로 활용합니다.
*   **Supabase (PostgreSQL)**: "Fact & Content" (RLS 필수 적용)
*   **Neo4j (Graph DB)**: "Context & Relation" (Unique Constraint 필수 적용)

---

## 2. Relational Schema (Supabase)

> **Security Note (RLS)**: 모든 테이블은 `Enable RLS` 처리되며, 기본 정책은 `auth.uid() = user_id` 입니다.

### 2.1 `users` (Supabase Auth 연동)
사용자 계정 정보. Supabase의 `auth.users`와 연동하여 커스텀 정보 저장.
*   `id` (UUID, PK): 사용자 고유 ID
*   `email` (Text): 이메일
*   `created_at`: 가입일

    *   *Trigger*: Supabase `auth.users`에 새로운 유저 가입(INSERT) 시, 자동으로 `public.users`에도 동일한 ID로 Row를 생성하는 PostgreSQL Function 및 Trigger 반드시 포함. (백엔드 의존성 제거)

### 2.2 `memories` (핵심 저장소)
수집된 지식의 원본(Chunk)과 메타데이터.
*   `id` (UUID, PK): 메모 고유 ID
*   `user_id` (UUID, FK): 소유자
*   `source_url` (Text, Nullable): 원본 출처 (URL)
*   `source_type` (Enum): 'WEB', 'PDF', 'NOTE'
*   `title` (Text): 제목
*   `content` (Text): 본문 내용 (Markdown)
*   `summary` (Text): LLM 요약본
*   `embedding` (Vector[1536]): 검색용 벡터 임베딩 (ada-002/v3-small)
*   `created_at`: 생성일
*   `updated_at`: 수정일

### 2.3 `chat_sessions`
소크라테스 에이전트와의 대화 세션.
*   `id` (UUID, PK)
*   `user_id` (UUID, FK)
*   `memory_id` (UUID, FK, Nullable): 특정 메모와 관련된 대화일 경우
*   `title` (Text): 대화 주제
*   `created_at`

### 2.4 `chat_messages`
대화 상세 내용.
*   `id` (UUID, PK)
*   `session_id` (UUID, FK)
*   `role` (Enum): 'USER', 'ASSISTANT', 'SYSTEM'
*   `content` (Text)
*   `created_at`

### 2.5 `task_queue` (Background Task Persistence)
백그라운드 작업의 안정성을 보장하기 위한 작업 대기열.
*   `id` (UUID, PK)
*   `user_id` (UUID, FK)
*   `task_type` (Enum): 'GRAPH_SYNC', 'VECTOR_EMBEDDING'
*   `status` (Enum): 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'
*   `payload` (JSONB): 작업에 필요한 데이터 (memoryId 등)
*   `created_at`
*   `updated_at`

---

## 3. Graph Ontology (Neo4j)

> **Integrity Note**: 모든 Node Label에 대해 `name` + `userId` 복합 Unique Constraint 생성 필수.

### 3.1 Node Labels (노드 타입)
모든 노드는 공통적으로 `userId` 속성을 가져 개인화된 그래프를 구성합니다.

*   `Concept`: 추상적인 개념, 기술, 이론 (e.g., "Artificial Intelligence", "React")
*   `Entity`: 구체적인 대상. 인물, 회사, 도구 (e.g., "Sam Altman", "Google", "VS Code")
*   `Project`: 사용자의 프로젝트 (e.g., "Memoir AI Dev")
*   `Chunk`: Supabase의 `memories`와 1:1 매핑되는 구체적인 지식 조각. (Graph와 RDB의 연결점)
    *   속성: `memoryId` (Supabase UUID), `title`, `url`

### 3.2 Relationship Types (엣지 타입)
관계는 방향성을 가지며, 사용자가 정의한 맥락을 표현합니다.

*   `RELATED_TO`: 일반적인 연관 관계 (e.g., "AI" - "Machine Learning")
*   `PART_OF`: 포함 관계 (e.g., "React" - "Frontend Tech")
*   `MENTIONS`: 텍스트(Chunk)가 개념을 언급함 (e.g., "Memory #123" - "Graph DB")
*   `INSPIRED_BY`: 아이디어나 생각의 출처
*   `USED_FOR`: 도구나 기술의 용도 (e.g., "Neo4j" - "Knowledge Graph")

### 3.3 Example Graph
(사용자가 "Memoir AI 개발을 위해 Neo4j를 공부했다"는 메모를 남겼을 때)

```cypher
(:Chunk {title: "Memoir Tech Spec", memoryId: "..."}) 
  -[:MENTIONS]-> (:Entity {name: "Neo4j"})
  -[:USED_FOR]-> (:Concept {name: "Knowledge Graph"})
  <-[:PART_OF]- (:Project {name: "Memoir AI"})
```

---

## 4. 데이터 흐름 (Data Flow)

1.  **Ingest**: `FastAPI`가 텍스트 수신 -> `Supabase`에 저장 (`memories` 테이블).
2.  **Vectorize**: 동시에 텍스트 임베딩 생성 -> `Supabase` `memories.embedding` 컬럼 업데이트.
3.  **Graph Sync (Background)**:
    *   LLM이 텍스트에서 [Entity A] - [Relation] - [Entity B] 추출.
    *   `Neo4j`에 노드 생성/Merger.
    *   `Neo4j`의 `Chunk` 노드 생성 후 `Supabase` ID 기록 (양방향 참조).
