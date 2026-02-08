# Memoir AI - API Specification

## 1. 개요
*   **Base URL**: `/api/v1`
*   **Authentication**: Bearer Token (JWT from Supabase Auth)
    *   Frontend에서 Supabase Login 후 Access Token을 헤더에 실어서 요청.
*   **Content-Type**: `application/json`
*   **Standard Error Response**:
    *   모든 API 에러는 아래 형식을 따릅니다.
    ```json
    {
      "error": {
        "code": "ERR_INVALID_INPUT", // 사람이 읽기 쉬운 코드
        "message": "URL format is invalid.", // 사용자에게 보여줄 수 있는 메시지
        "details": { ... } // (Optional) 디버깅용 추가 정보
      }
    }
    ```

---

## 2. Authentication (Auth)
*Auth는 기본적으로 클라이언트(React)에서 Supabase SDK를 통해 직접 처리하지만, 백엔드 검증이 필요한 경우를 위해 기재합니다.*

### `GET /auth/me`
*   **Description**: 현재 토큰의 유효성 검사 및 사용자 정보 반환.
*   **Response**: `200 OK`
    ```json
    {
      "id": "uuid",
      "email": "user@example.com",
      "role": "authenticated"
    }
    ```

---

## 3. Memories (지식 저장소)

### `POST /memories`
*   **Description**: 새로운 지식(URL, 텍스트)을 수집(Ingest)합니다.
*   **Request Body**:
    ```json
    {
      "sourceType": "WEB" | "NOTE",
      "url": "https://example.com/article...",
      "content": "Raw content if note...",
      "memo": "User's initial thought (optional)"
    }
    ```
*   **Response**: `201 Created`
    ```json
    {
      "id": "memory_uuid",
      "status": "processing" // 백그라운드에서 임베딩/그래프 작업 시작
    }
    ```

### `GET /memories`
*   **Description**: 저장된 메모 리스트 조회 (Pagination).
*   **Query Params**: `page`, `limit`, `search` (simple text search)
*   **Response**: `200 OK`
    ```json
    {
      "items": [
        {
          "id": "uuid",
          "title": "Article Title",
          "summary": "Short summary...",
          "createdAt": "ISO8601"
        }
      ],
      "total": 100
    }
    ```

### `GET /memories/{id}`
*   **Description**: 특정 메모 상세 조회.
*   **Response**: `200 OK`
    ```json
    {
      "id": "uuid",
      "title": "Title",
      "content": "Full Markdown Content...",
      "graph_data": { ... } // 연관된 그래프 노드 정보 (Light)
    }
    ```

### `DELETE /memories/{id}`
*   **Description**: 메모 삭제 (Graph 및 Vector 데이터 포함).

---

## 4. Chat (Socratic Dialogue)

### `POST /chat/sessions`
*   **Description**: 새로운 대화 세션 시작.
*   **Request Body**:
    ```json
    {
      "memoryId": "uuid" // (Optional) 특정 메모에 대한 대화일 경우
    }
    ```
*   **Response**: `201 Created`
    ```json
    { "sessionId": "uuid" }
    ```

### `POST /chat/sessions/{sessionId}/messages` (Streaming)
*   **Description**: 사용자 메시지 전송 및 LLM 스트리밍 응답.
*   **Request Body**:
    ```json
    {
      "content": "사용자 질문..."
    }
    ```
*   **Response**: `Text/Event-Stream` (Server-Sent Events)
    *   **Events Types**:
        *   `event: token` - LLM 생성 토큰 (data: "안")
        *   `event: error` - 에러 발생 (data: "{\"code\": ...}")
        *   `event: done` - 스트리밍 종료
    *   `[DONE]` 이벤트 수신 시 종료.

---

## 5. Graph (Knowledge Navigation)

### `GET /graph/explore`
*   **Description**: 지식 그래프 탐색. `react-force-graph-2d` 호환 포맷.
*   **Query Params**:
    *   `centerParams`: 중심이 될 키워드 혹은 Node ID (없으면 전체 상위 노드)
    *   `depth`: 1 (default) - 연결 깊이
*   **Response**: `200 OK`
    ```json
    {
      "nodes": [
        { "id": "1", "name": "AI", "val": 1 }, // val for node size
        { "id": "2", "name": "LLM", "val": 1 }
      ],
      "links": [
        { "source": "1", "target": "2", "name": "RELATED_TO" }
      ]
    }
    ```

### `POST /graph/sync` (Recovery)
*   **Description**: 그래프 동기화 실패(또는 누락)된 메모에 대해 강제로 재처리를 요청합니다.
*   **Request Body**:
    ```json
    {
      "memoryId": "uuid" // 특정 ID 지정 시 해당 건만, 없을 시 Failed 상태 전체 재시도
    }
    ```
*   **Response**: `200 OK`
    ```json
    {
       "triggered": 1,
       "message": "Background sync started"
    }
    ```
