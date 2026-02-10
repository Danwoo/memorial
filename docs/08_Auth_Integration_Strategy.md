# Memoir AI - 통합 인증 + 연동 전략 설계서

> **버전**: v1.0 Draft
> **작성일**: 2026-02-10
> **상태**: Draft - 리뷰 필요

---

## 1. 현재 상태 분석 (As-Is)

### 1.1 인증 (Authentication)
| 항목 | 현재 상태 |
|---|---|
| Auth 기반 | Supabase Auth (Google OAuth + Email/Password) |
| 프론트엔드 | `AuthContext.tsx`에서 `supabase.auth.signInWithOAuth({ provider: 'google' })` |
| 백엔드 | `auth.py`에서 Supabase `/auth/v1/user` 엔드포인트로 JWT 검증 |
| 토큰 관리 | `localStorage.auth_token`에 Supabase access_token 저장 |
| Dev Bypass | `DEBUG=True`일 때 `DEFAULT_USER_ID`로 우회 |

### 1.2 카카오 연동 (Kakao Integration)
| 항목 | 현재 상태 |
|---|---|
| 용도 | "나에게 보내기" 메시지 전송 전용 (인증 아님) |
| OAuth 플로우 | 별도 OAuth (Supabase Auth 경유 아님) |
| scope | `talk_message` |
| 토큰 저장 | `kakao_tokens` 테이블 (user_id, access_token, refresh_token, expires_at) |
| 연결 관리 | Settings 페이지에서 연결/해제 |

### 1.3 Chrome Extension
| 항목 | 현재 상태 |
|---|---|
| 상태 | Manifest V3 스켈레톤만 존재 |
| 인증 | 없음 (localhost:8000에 인증 없이 POST) |
| 기능 | 현재 탭의 URL을 `/memories`에 POST하는 수준 |

### 1.4 핵심 문제점
1. **카카오가 인증 수단이 아님** - 카카오 OAuth는 "메시지 전송" 권한만 획득하며, Supabase Auth와 무관
2. **Account Linking 불가** - Google 계정과 카카오 계정이 완전히 분리된 시스템
3. **Chrome Extension이 인증 없이 동작** - 누구나 API 호출 가능한 보안 취약점
4. **카카오톡 메시지 수신 불가** - "나에게 보내기"는 발신 전용, 수신 트리거 없음

---

## 2. 목표 상태 (To-Be) 아키텍처

### 2.1 시스템 전체 구조

```
                         +-----------------+
                         |   Supabase Auth |
                         |  (ID Provider)  |
                         +--------+--------+
                                  |
                    +-------------+-------------+
                    |                           |
              Google OAuth                Kakao OAuth
              (provider:google)           (provider:kakao)
                    |                           |
                    v                           v
         +------------------+        +-------------------+
         | Chrome Extension |        |  Kakao Chatbot    |
         | (웹 클리핑)       |        |  (메시지 수집/발신) |
         +--------+---------+        +---------+---------+
                  |                            |
                  v                            v
         +------------------------------------------------+
         |           FastAPI Backend (API v1)              |
         |  /memories (ingest)  |  /integrations/kakao/*  |
         +------------------------+------------------------+
                  |                            |
                  v                            v
         +------------------+        +-------------------+
         | Supabase (PG)    |        | Kakao i OpenBuilder|
         | memories, tokens |        | Skill Server       |
         +------------------+        +-------------------+
```

### 2.2 인증 전략: Supabase Auth 멀티 프로바이더

**핵심 결정**: Supabase Auth가 **단일 인증 허브** 역할을 하며, Google과 Kakao 모두 Supabase Auth의 OAuth Provider로 등록합니다.

| 프로바이더 | 인증 역할 | 연동 기능 | 필요 scope |
|---|---|---|---|
| Google | 회원가입/로그인 | Chrome Extension (웹 클리핑) | `email`, `profile` |
| Kakao | 회원가입/로그인 | 카카오톡 채널 봇 (메시지 수집 + 다이제스트) | `account_email`, `profile_nickname`, `talk_message`, `friends` |

**Account Linking 방식**: Supabase Auth의 **Automatic Identity Linking** 활용
- 동일 이메일 주소의 Google/Kakao 계정은 자동으로 같은 user에 연결
- 다른 이메일인 경우 `supabase.auth.linkIdentity()` API로 수동 연결

---

## 3. 사용자 플로우 (User Flows)

### 3.1 시나리오 A: Google로 시작하는 사용자

```
[1] 사용자가 AuthView에서 "Google로 로그인" 클릭
    -> Supabase Auth signInWithOAuth({ provider: 'google' })
    -> 회원가입/로그인 완료 (Supabase user 생성)

[2] Settings 페이지에서 "카카오 계정 연결" 클릭
    -> 로그인 상태에서 supabase.auth.linkIdentity({ provider: 'kakao' })
    -> Kakao OAuth 동의 화면 (talk_message scope 포함)
    -> 콜백 후 동일 user에 Kakao identity 추가
    -> Kakao access_token을 provider_tokens에서 추출하여 kakao_tokens에 저장

[3] Settings 페이지에서 "Memoir 카카오 채널 추가" 안내
    -> QR코드 또는 채널 검색 링크 제공
    -> 사용자가 카카오톡에서 채널 친구 추가

[4] Chrome Extension에서 "로그인" 클릭
    -> Extension이 웹앱 auth 세션을 공유하거나 별도 OAuth 수행
    -> 인증된 상태에서 웹 클리핑 가능

결과: Google 인증 + Kakao 연동 + Chrome Extension + 카카오톡 봇 모두 활성화
```

### 3.2 시나리오 B: Kakao로 시작하는 사용자

```
[1] 사용자가 AuthView에서 "카카오로 로그인" 클릭
    -> Supabase Auth signInWithOAuth({ provider: 'kakao' })
    -> 회원가입/로그인 완료
    -> Kakao OAuth token은 Supabase가 내부 관리 + 우리가 별도 저장

[2] 카카오톡 채널 봇 연동은 바로 가능 (Kakao identity 이미 존재)
    -> Settings에서 "Memoir 채널 추가" 진행

[3] (선택) Settings에서 "Google 계정 연결" 클릭
    -> supabase.auth.linkIdentity({ provider: 'google' })
    -> Chrome Extension 사용 가능해짐

결과: Kakao 인증 + 카카오톡 봇 활성화 / Google 연결 시 Extension도 활성화
```

### 3.3 시나리오 C: 카카오톡 채널에서 메시지 수신

```
[1] 사용자가 Memoir 카카오톡 채널에 메시지/링크 전송
    -> 카카오 오픈빌더가 스킬 서버(우리 백엔드)에 POST 전달
    -> payload: { userRequest: { utterance: "https://...", user: { id: "botUserKey" } } }

[2] 백엔드 스킬 서버 엔드포인트가 수신
    -> botUserKey와 kakao_channel_mappings 테이블에서 user_id 조회
    -> utterance에서 URL 또는 텍스트 추출
    -> ingest_service로 memory 생성

[3] 즉시 응답으로 "저장 완료" 메시지 반환
    -> 카카오톡 채널에서 사용자에게 확인 메시지 표시

[4] (비동기) 임베딩 + 그래프 동기화 백그라운드 처리
```

### 3.4 시나리오 D: Chrome Extension 웹 클리핑

```
[1] Extension 팝업에서 로그인 상태 확인
    -> chrome.storage.local에서 세션 토큰 로드
    -> 없으면 웹앱 로그인 페이지로 리다이렉트

[2] 현재 탭에서 "Save to Memoir" 클릭
    -> content script가 페이지 본문 추출 (title, url, content)
    -> Bearer 토큰과 함께 POST /api/v1/memories 호출
    -> 저장 결과 표시

[3] (선택) 텍스트 선택 후 우클릭 -> "Save Selection to Memoir"
    -> 선택된 텍스트를 source_type: 'CLIP'으로 저장
```

---

## 4. 인증 아키텍처 상세 설계

### 4.1 Supabase Auth 설정 변경

**Supabase Dashboard에서 설정할 내용:**

1. **Authentication > Providers > Kakao 활성화**
   - Client ID: Kakao REST API Key
   - Client Secret: Kakao Client Secret (보안 > Client Secret 코드)
   - Redirect URL: `https://<project-ref>.supabase.co/auth/v1/callback`

2. **Authentication > URL Configuration**
   - Site URL: `https://memoir.ai` (또는 `http://localhost:5173`)
   - Redirect URLs에 추가:
     - `http://localhost:5173/*` (개발)
     - `https://memoir.ai/*` (프로덕션)
     - `https://<extension-id>.chromiumapp.org/*` (Chrome Extension)

3. **Authentication > General > Enable Manual Linking**
   - 이메일이 다른 계정도 수동 연결 가능하도록 활성화

### 4.2 Kakao Developers 설정

**기존 앱을 확장하거나 새 앱 생성:**

1. **카카오 로그인 활성화**
   - Redirect URI 추가: `https://<project-ref>.supabase.co/auth/v1/callback`
   - (기존 `localhost:8000/.../kakao/callback`은 채널 봇 전용으로 유지할 수 있음)

2. **동의항목(Consent Items) 설정**
   - `account_email` (필수) - Supabase identity linking에 필요
   - `profile_nickname` (선택)
   - `profile_image` (선택)
   - `talk_message` (필수) - 나에게 보내기 (다이제스트 전송)
   - `friends` (선택) - 채널 메시지 발송 시 필요할 수 있음

3. **OpenID Connect 활성화**
   - Supabase Auth Kakao provider가 OIDC를 사용하므로 활성화 필수

### 4.3 프론트엔드 AuthContext 변경

현재 `signInWithGoogle`만 있는 구조에서, `signInWithKakao`를 추가하고 identity linking 메서드를 추가합니다.

```typescript
// AuthContext.tsx에 추가할 메서드들
interface AuthContextValue {
  // ... 기존 메서드들
  signInWithKakao: () => Promise<void>
  linkProvider: (provider: 'google' | 'kakao') => Promise<void>
  unlinkProvider: (identityId: string) => Promise<void>
  getLinkedProviders: () => Promise<UserIdentity[]>
}
```

**signInWithKakao 구현:**
```typescript
const signInWithKakao = useCallback(async () => {
  if (!supabase) throw new Error('Supabase is not configured')
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'kakao',
    options: {
      redirectTo: `${window.location.origin}/`,
      scopes: 'account_email profile_nickname talk_message',
    },
  })
  if (error) throw error
}, [])
```

**linkProvider 구현 (로그인 후 추가 프로바이더 연결):**
```typescript
const linkProvider = useCallback(async (provider: 'google' | 'kakao') => {
  if (!supabase) throw new Error('Supabase is not configured')
  const { error } = await supabase.auth.linkIdentity({
    provider,
    options: {
      redirectTo: `${window.location.origin}/settings?linked=${provider}`,
      scopes: provider === 'kakao'
        ? 'account_email profile_nickname talk_message'
        : undefined,
    },
  })
  if (error) throw error
}, [])
```

### 4.4 Kakao Token 이중 관리 전략

**문제**: Supabase Auth는 Kakao OAuth 토큰을 인증 목적으로만 사용하고, `talk_message` scope의 access_token을 직접 노출하지 않습니다. 하지만 카카오톡 메시지 전송에는 사용자의 Kakao access_token이 필요합니다.

**해결책: Session의 provider_token 활용**

```
Supabase Auth Kakao 로그인
    |
    v
onAuthStateChange 이벤트에서
session.provider_token (Kakao access_token)
session.provider_refresh_token (Kakao refresh_token)
    |
    v
백엔드 POST /integrations/kakao/store-token 호출
    |
    v
kakao_tokens 테이블에 저장 (기존 로직 재활용)
```

**주의**: `provider_token`은 세션 생성 시점에만 사용 가능하며, Supabase가 자동 갱신하지 않습니다. 따라서:
- 최초 로그인/링크 시 provider_token을 캡처하여 별도 저장
- 만료 시 Kakao refresh_token으로 자체 갱신 (기존 `_refresh_token` 로직 유지)
- refresh_token도 만료 시 re-link 필요 (Settings에서 "카카오 재연결" 버튼)

### 4.5 백엔드 인증 미들웨어 변경

**변경 불필요**: 현재 `auth.py`의 `get_current_user`는 Supabase `/auth/v1/user`로 JWT를 검증합니다. Supabase Auth에 Kakao provider를 추가해도 JWT 형식은 동일하므로, 백엔드 인증 로직 변경이 필요 없습니다.

단, 프로바이더 정보를 확인하려면:
```python
# user_data에서 추가 정보 활용 가능
user_data["app_metadata"]["provider"]  # 'google' 또는 'kakao'
user_data["app_metadata"]["providers"]  # ['google', 'kakao']
```

---

## 5. 카카오톡 채널 봇 상세 설계

### 5.1 아키텍처 개요

```
사용자 카카오톡
    |
    | (채널에 메시지 전송)
    v
카카오 i 오픈빌더
    |
    | HTTP POST (스킬 요청)
    v
FastAPI Skill Server (/api/v1/integrations/kakao/webhook)
    |
    |-- utterance에서 URL/텍스트 추출
    |-- botUserKey로 user_id 조회
    |-- ingest_service.create_memory()
    |
    v
즉시 JSON 응답 (카카오톡 채널 메시지로 표시)
```

### 5.2 카카오 i 오픈빌더 설정

1. **카카오톡 채널 생성**: "Memoir AI" 채널 (카카오톡 채널 관리자센터)
2. **오픈빌더 봇 생성**: 카카오 i 오픈빌더에서 봇 생성 후 채널 연결
3. **스킬 등록**: 우리 백엔드 URL을 스킬 서버로 등록
4. **폴백 블록에 스킬 연결**: 모든 사용자 발화를 우리 스킬 서버로 라우팅

### 5.3 Skill Server 엔드포인트 설계

**요청 (카카오 오픈빌더 -> 우리 서버):**
```json
POST /api/v1/integrations/kakao/webhook

{
  "userRequest": {
    "timezone": "Asia/Seoul",
    "utterance": "https://techcrunch.com/interesting-article",
    "user": {
      "id": "abc123_botUserKey",
      "type": "botUserKey",
      "properties": {
        "plusfriendUserKey": "pf_xyz789"
      }
    },
    "callbackUrl": "https://bot-api.kakao.com/callback/..."
  },
  "bot": {
    "id": "bot_id",
    "name": "Memoir AI"
  },
  "action": {
    "name": "save_memory",
    "params": {}
  }
}
```

**응답 (우리 서버 -> 카카오 오픈빌더):**

성공 시:
```json
{
  "version": "2.0",
  "template": {
    "outputs": [
      {
        "simpleText": {
          "text": "저장 완료! 'Interesting Article Title'이 Memoir에 추가되었습니다."
        }
      }
    ],
    "quickReplies": [
      {
        "label": "최근 저장 목록",
        "action": "message",
        "messageText": "#최근목록"
      }
    ]
  }
}
```

미등록 사용자 시:
```json
{
  "version": "2.0",
  "template": {
    "outputs": [
      {
        "textCard": {
          "title": "Memoir AI에 연결해주세요",
          "description": "카카오톡으로 메모를 저장하려면 먼저 Memoir 계정과 연결해야 합니다.",
          "buttons": [
            {
              "label": "연결하기",
              "action": "webLink",
              "webLinkUrl": "https://memoir.ai/settings?connect=kakao-channel"
            }
          ]
        }
      }
    ]
  }
}
```

### 5.4 botUserKey -> user_id 매핑

**문제**: 카카오 오픈빌더는 `botUserKey`로 사용자를 식별하지만, 우리 시스템은 Supabase `user_id`를 사용합니다. 이 둘을 연결해야 합니다.

**해결책: 채널 연결 등록 플로우**

```
[1] Settings 페이지에서 "카카오 채널 연결" 클릭
    -> 고유 연결 코드 생성 (예: "MEMOIR-A3X7K2")
    -> 화면에 "카카오톡에서 Memoir AI 채널에 이 코드를 보내주세요" 안내

[2] 사용자가 카카오톡 채널에 연결 코드 전송
    -> 스킬 서버가 utterance에서 코드 패턴 감지
    -> 연결 코드로 pending_channel_links 조회
    -> botUserKey <-> user_id 매핑을 kakao_channel_mappings에 저장

[3] 연결 완료 응답
    -> "연결 완료! 이제 이 채널에 링크나 메모를 보내면 자동 저장됩니다."
```

### 5.5 채널 봇 명령어 체계

| 발화 패턴 | 동작 | 응답 |
|---|---|---|
| URL (https://...) | URL 크롤링 -> memory 저장 | "'{title}' 저장 완료" |
| 일반 텍스트 | source_type: 'KAKAO_CHAT'으로 memory 저장 | "메모 저장 완료" |
| `#최근목록` | 최근 5개 memory 목록 | ListCard 형태로 반환 |
| `#다이제스트` | 오늘의 다이제스트 요약 | 다이제스트 텍스트 |
| `#연결 XXXX` | 채널-계정 연결 | 연결 성공/실패 메시지 |
| `#해제` | 채널 연결 해제 | 해제 완료 메시지 |
| `#도움말` | 명령어 가이드 | 사용법 안내 |

### 5.6 다이제스트 발송 (채널 -> 사용자)

기존 "나에게 보내기" 대신 **채널 메시지 발송 API** 사용:

```
POST https://kapi.kakao.com/v1/api/talk/channels/message/send
```

- 카카오톡 채널의 친구에게 메시지를 보내는 API
- 채널 관리자 권한(비즈앱)이 필요
- 알림톡/친구톡과 달리 무료 (일일 발송 한도 있음)
- 사용자가 채널 친구인 경우에만 발송 가능

**대안 검토:**
| 방식 | 비용 | 제약 | 적합성 |
|---|---|---|---|
| 나에게 보내기 (기존) | 무료 | 사용자 동의 필요, 수신 트리거 없음 | 발신 전용으로 활용 가능 |
| 채널 메시지 | 무료 | 채널 친구 대상만, 일일 한도 | 가장 적합 |
| 알림톡 | 건당 7-8원 | 템플릿 심사 필요 | 과도한 비용 |
| 친구톡 | 건당 15-25원 | 광고성 메시지용 | 부적합 |

**결론**: 채널 메시지를 기본으로, 나에게 보내기를 보조 수단으로 유지

---

## 6. Chrome Extension 상세 설계

### 6.1 인증 연계 방식

**방식: 웹앱 세션 공유 (Cookie-based)**

Chrome Extension은 웹앱의 인증 상태를 활용합니다:

```
[Option A] Cookie/Storage 기반 세션 공유
    1. 사용자가 웹앱(memoir.ai)에서 로그인
    2. Supabase가 auth cookie 설정
    3. Extension이 chrome.cookies API로 세션 읽기
    4. 읽은 토큰으로 API 호출

[Option B] Extension 내 독립 OAuth (권장)
    1. Extension 팝업에서 "Google로 로그인" 클릭
    2. chrome.identity.launchWebAuthFlow()로 Supabase OAuth 시작
    3. 콜백에서 세션 토큰 수신
    4. chrome.storage.local에 토큰 저장
    5. 이후 API 호출 시 토큰 사용
```

**Option B 상세 구현 (권장):**

```javascript
// background.js
const SUPABASE_URL = 'https://<project-ref>.supabase.co'
const SUPABASE_ANON_KEY = '<anon-key>'

async function signInWithGoogle() {
  const redirectUrl = chrome.identity.getRedirectURL()
  // redirectUrl = https://<extension-id>.chromiumapp.org/

  const authUrl = `${SUPABASE_URL}/auth/v1/authorize?` +
    `provider=google&` +
    `redirect_to=${encodeURIComponent(redirectUrl)}`

  const responseUrl = await chrome.identity.launchWebAuthFlow({
    url: authUrl,
    interactive: true,
  })

  // responseUrl에서 access_token, refresh_token 추출
  const url = new URL(responseUrl)
  const hashParams = new URLSearchParams(url.hash.substring(1))
  const accessToken = hashParams.get('access_token')
  const refreshToken = hashParams.get('refresh_token')

  await chrome.storage.local.set({
    supabase_access_token: accessToken,
    supabase_refresh_token: refreshToken,
  })

  return accessToken
}
```

### 6.2 Extension manifest.json 업데이트

```json
{
  "manifest_version": 3,
  "name": "Memoir Scout",
  "version": "1.0",
  "description": "Save current page to Memoir AI",
  "permissions": [
    "activeTab",
    "scripting",
    "storage",
    "identity"
  ],
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["content.js"],
      "run_at": "document_idle"
    }
  ],
  "host_permissions": [
    "https://<project-ref>.supabase.co/*",
    "https://memoir-api.fly.dev/*"
  ],
  "oauth2": {
    "client_id": "<google-client-id>.apps.googleusercontent.com",
    "scopes": ["email", "profile"]
  }
}
```

### 6.3 데이터 흐름

```
[사용자 클릭] "Save to Memoir"
       |
       v
[content.js] 페이지 본문 추출
  - document.title
  - window.location.href
  - Readability.js로 본문 텍스트 추출
  - 선택된 텍스트 (있는 경우)
       |
       v
[popup.js] API 호출
  POST /api/v1/memories
  Headers: { Authorization: Bearer <token> }
  Body: {
    source_type: "WEB",
    url: "https://...",
    content: "<extracted text>",
    memo: "<user's optional note>"
  }
       |
       v
[백엔드] 기존 ingest 파이프라인으로 처리
```

---

## 7. Settings 페이지 UI 설계

### 7.1 레이아웃 구조

```
+---------------------------------------------------------+
|  설정                                                     |
|  서비스 연동 및 계정 설정을 관리합니다                        |
+---------------------------------------------------------+
|                                                          |
|  [계정 정보]                                              |
|  +----------------------------------------------------+  |
|  |  이메일: user@gmail.com                             |  |
|  |  로그인 방식: Google                                 |  |
|  |  가입일: 2026-01-15                                  |  |
|  +----------------------------------------------------+  |
|                                                          |
|  [연결된 계정]                                            |
|  +----------------------------------------------------+  |
|  |  [G] Google    user@gmail.com         [연결됨]      |  |
|  |  [K] Kakao     kakao_user@kakao.com   [연결하기]    |  |
|  +----------------------------------------------------+  |
|                                                          |
|  [서비스 연동]                                            |
|  +----------------------------------------------------+  |
|  |  카카오톡 채널 봇                                    |  |
|  |  메시지와 링크를 카카오톡으로 보내 자동 저장합니다       |  |
|  |                                                      |  |
|  |  상태: [채널 미연결]                                  |  |
|  |  [카카오 채널 연결하기] 버튼                           |  |
|  |                                                      |  |
|  |  -- 연결 후 --                                       |  |
|  |  상태: [연결됨] (채널: Memoir AI)                     |  |
|  |  다이제스트 발송: [매일 오후 9시]  [수정]              |  |
|  |  [연결 해제] 버튼                                    |  |
|  +----------------------------------------------------+  |
|  +----------------------------------------------------+  |
|  |  Chrome Extension                                   |  |
|  |  웹 페이지를 한 클릭으로 저장합니다                    |  |
|  |                                                      |  |
|  |  상태: Google 계정 연결 필요                          |  |
|  |  -- 또는 --                                          |  |
|  |  상태: [사용 가능]                                    |  |
|  |  [Extension 설치 가이드]                              |  |
|  +----------------------------------------------------+  |
|                                                          |
+---------------------------------------------------------+
```

### 7.2 컴포넌트 구조

```
SettingsView
  +-- AccountInfoSection
  |     +-- UserProfile (이메일, 가입일)
  |     +-- LinkedProviders
  |           +-- ProviderCard (Google) [연결됨/연결하기/해제]
  |           +-- ProviderCard (Kakao)  [연결됨/연결하기/해제]
  |
  +-- IntegrationsSection
        +-- KakaoChannelCard
        |     +-- ChannelStatus (미연결/연결중/연결됨)
        |     +-- LinkingFlow (연결 코드 표시)
        |     +-- DigestSettings (발송 시간 설정)
        |
        +-- ChromeExtensionCard
              +-- ExtensionStatus (Google 필요/사용 가능)
              +-- InstallGuide (설치 링크)
```

---

## 8. 데이터 모델 변경

### 8.1 신규 테이블

#### `kakao_channel_mappings` (카카오 채널 <-> 사용자 매핑)
```sql
CREATE TABLE kakao_channel_mappings (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  bot_user_key TEXT NOT NULL UNIQUE,
  plusfriend_user_key TEXT,
  channel_status TEXT DEFAULT 'active' CHECK (channel_status IN ('active', 'inactive')),
  linked_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_channel_mappings_bot_user_key ON kakao_channel_mappings(bot_user_key);
CREATE INDEX idx_channel_mappings_user_id ON kakao_channel_mappings(user_id);

ALTER TABLE kakao_channel_mappings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own mappings"
  ON kakao_channel_mappings FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own mappings"
  ON kakao_channel_mappings FOR ALL
  USING (auth.uid() = user_id);
```

#### `pending_channel_links` (채널 연결 대기 코드)
```sql
CREATE TABLE pending_channel_links (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  link_code TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ DEFAULT now(),
  expires_at TIMESTAMPTZ DEFAULT (now() + interval '30 minutes'),
  used BOOLEAN DEFAULT false
);

CREATE INDEX idx_pending_links_code ON pending_channel_links(link_code);

ALTER TABLE pending_channel_links ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own pending links"
  ON pending_channel_links FOR SELECT
  USING (auth.uid() = user_id);
```

#### `user_integrations` (통합 연동 상태 관리)
```sql
CREATE TABLE user_integrations (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL CHECK (provider IN ('google', 'kakao')),
  integration_type TEXT NOT NULL CHECK (integration_type IN (
    'auth',              -- Supabase Auth identity
    'kakao_channel',     -- 카카오톡 채널 봇
    'kakao_message',     -- 카카오톡 나에게 보내기
    'chrome_extension'   -- Chrome Extension
  )),
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'expired')),
  metadata JSONB DEFAULT '{}',
  connected_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(user_id, provider, integration_type)
);

ALTER TABLE user_integrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own integrations"
  ON user_integrations FOR SELECT
  USING (auth.uid() = user_id);
```

### 8.2 기존 테이블 변경

#### `kakao_tokens` 테이블 (변경)
```sql
-- 기존 구조 유지하되, token_source 컬럼 추가
ALTER TABLE kakao_tokens
  ADD COLUMN token_source TEXT DEFAULT 'oauth_direct'
    CHECK (token_source IN ('oauth_direct', 'supabase_provider', 'channel_bot'));
```

#### `memories` 테이블 (변경)
```sql
-- source_type enum에 새 값 추가
-- 기존: 'WEB', 'PDF', 'NOTE'
-- 추가: 'KAKAO_CHAT', 'CLIP' (Chrome Extension 텍스트 선택)
ALTER TABLE memories
  DROP CONSTRAINT IF EXISTS memories_source_type_check;

ALTER TABLE memories
  ADD CONSTRAINT memories_source_type_check
  CHECK (source_type IN ('WEB', 'PDF', 'NOTE', 'KAKAO_CHAT', 'CLIP'));
```

### 8.3 ERD 변경 요약

```
auth.users (Supabase)
    |
    +-- 1:N -- kakao_tokens (기존, 토큰 관리)
    +-- 1:N -- kakao_channel_mappings (신규, 채널 봇 매핑)
    +-- 1:N -- pending_channel_links (신규, 연결 코드)
    +-- 1:N -- user_integrations (신규, 연동 상태 종합)
    +-- 1:N -- memories (기존, source_type 확장)
```

---

## 9. API 엔드포인트 변경

### 9.1 신규 엔드포인트

#### 카카오 채널 봇 Webhook
```
POST /api/v1/integrations/kakao/webhook
  - 인증: 카카오 오픈빌더 서버 IP 화이트리스트 또는 시크릿 검증
  - 요청: 카카오 오픈빌더 스킬 요청 포맷
  - 응답: 카카오 오픈빌더 스킬 응답 포맷 (version 2.0)
```

#### 채널 연결 코드 생성
```
POST /api/v1/integrations/kakao/channel/link-code
  - 인증: Bearer Token (require_auth)
  - 응답: { code: "MEMOIR-A3X7K2", expires_at: "...", instructions: "..." }
```

#### 채널 연결 상태 조회
```
GET /api/v1/integrations/kakao/channel/status
  - 인증: Bearer Token
  - 응답: { connected: true, bot_user_key: "...", linked_at: "..." }
```

#### 채널 연결 해제
```
POST /api/v1/integrations/kakao/channel/disconnect
  - 인증: Bearer Token
  - 응답: { success: true }
```

#### Provider Token 저장 (Supabase OAuth 후)
```
POST /api/v1/integrations/kakao/store-provider-token
  - 인증: Bearer Token
  - 요청: { provider_token: "...", provider_refresh_token: "..." }
  - 용도: Supabase Kakao 로그인 후 provider_token을 kakao_tokens에 저장
```

#### 연동 상태 종합 조회
```
GET /api/v1/integrations/status
  - 인증: Bearer Token
  - 응답: {
      providers: {
        google: { linked: true, email: "..." },
        kakao: { linked: true, email: "..." }
      },
      integrations: {
        kakao_channel: { connected: true, linked_at: "..." },
        kakao_message: { connected: true },
        chrome_extension: { available: true }  // Google 연결 여부 기반
      }
    }
```

### 9.2 기존 엔드포인트 변경

| 엔드포인트 | 변경 내용 |
|---|---|
| `GET /integrations/kakao/auth` | "나에게 보내기" 전용으로 유지 (채널 봇과 분리) |
| `GET /integrations/kakao/callback` | 동일 유지 |
| `POST /integrations/kakao/send` | 채널 메시지 또는 나에게 보내기 선택 로직 추가 |
| `GET /auth/me` | `providers` 정보 포함하도록 확장 |

---

## 10. 환경변수 추가

### 10.1 Backend Settings 추가 항목

```python
class Settings(BaseSettings):
    # ... 기존 설정

    # Kakao API (확장)
    KAKAO_REST_API_KEY: str | None = None
    KAKAO_CLIENT_SECRET: str | None = None        # 신규: Kakao 보안 > Client Secret
    KAKAO_REDIRECT_URI: str = "..."                # 기존 유지
    KAKAO_CHANNEL_ID: str | None = None            # 신규: 채널 고유 ID
    KAKAO_BOT_ID: str | None = None                # 신규: 오픈빌더 봇 ID
    KAKAO_SKILL_SECRET: str | None = None          # 신규: 스킬 서버 인증용

    # Chrome Extension
    CHROME_EXTENSION_ID: str | None = None         # 신규: Extension ID (CORS용)
```

### 10.2 CORS Origins 추가

```python
CORS_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://localhost:3000",
    "chrome-extension://<extension-id>",  # Chrome Extension
]
```

---

## 11. 구현 우선순위 (Phased Rollout)

### Phase 1: Kakao Auth + Account Linking (1주)

**목표**: Kakao로도 로그인 가능 + 기존 Google 사용자와 연결

| 작업 | 담당 | 의존성 |
|---|---|---|
| Supabase Dashboard에 Kakao Provider 추가 | 인프라 | Kakao Developers 앱 설정 |
| Kakao Developers 앱에 Supabase Redirect URI 추가 | 인프라 | 없음 |
| AuthView에 "카카오로 로그인" 버튼 추가 | 프론트엔드 | Supabase 설정 완료 |
| AuthContext에 signInWithKakao 메서드 추가 | 프론트엔드 | 없음 |
| provider_token 캡처 -> kakao_tokens 저장 로직 | 프론트/백엔드 | 없음 |
| 기존 "나에게 보내기" 동작 확인 | QA | Phase 1 전체 |

**완료 기준**: Google OR Kakao로 회원가입/로그인 가능, 기존 기능 정상 동작

### Phase 2: Settings 페이지 리뉴얼 + Provider 관리 (1주)

**목표**: 멀티 프로바이더 관리 UI 완성

| 작업 | 담당 | 의존성 |
|---|---|---|
| Settings 페이지 리디자인 (계정 정보, 연결 계정 섹션) | 프론트엔드 | Phase 1 |
| linkIdentity / unlinkIdentity UI 구현 | 프론트엔드 | Phase 1 |
| GET /integrations/status 엔드포인트 | 백엔드 | user_integrations 테이블 |
| user_integrations 테이블 생성 마이그레이션 | 백엔드 | 없음 |

**완료 기준**: Settings에서 프로바이더 연결/해제 가능, 연동 상태 한눈에 확인

### Phase 3: 카카오톡 채널 봇 (2주)

**목표**: 카카오톡 채널로 메시지/링크를 보내면 자동 저장

| 작업 | 담당 | 의존성 |
|---|---|---|
| 카카오톡 채널 생성 (관리자센터) | PM/인프라 | 사업자 인증 |
| 카카오 i 오픈빌더 봇 생성 + 채널 연결 | PM/인프라 | 채널 생성 |
| Skill Server 엔드포인트 구현 (/webhook) | 백엔드 | 없음 |
| kakao_channel_mappings, pending_channel_links 테이블 | 백엔드 | 없음 |
| 채널 연결 플로우 (연결 코드 생성/검증) | 백엔드 | 테이블 생성 |
| URL 감지 + 크롤링 -> memory 저장 로직 | 백엔드 | ingest_service |
| 명령어 체계 (#최근목록, #다이제스트 등) | 백엔드 | 기존 서비스 |
| Settings에 채널 연결 UI | 프론트엔드 | Phase 2 |
| 다이제스트 발송을 채널 메시지로 전환 | 백엔드 | 채널 봇 완성 |

**완료 기준**: 카카오톡 채널에 URL 전송 시 자동 저장, 다이제스트 수신

### Phase 4: Chrome Extension 고도화 (1주)

**목표**: 인증 연계된 웹 클리핑 Extension

| 작업 | 담당 | 의존성 |
|---|---|---|
| Extension에 Supabase OAuth 연동 (chrome.identity) | 프론트엔드 | Phase 1 Google Auth |
| content.js: Readability.js 기반 본문 추출 | 프론트엔드 | 없음 |
| popup.js: 인증 상태 관리 + 저장 UI | 프론트엔드 | OAuth 연동 |
| background.js: 토큰 관리 + 자동 갱신 | 프론트엔드 | OAuth 연동 |
| Context menu: "Save Selection to Memoir" | 프론트엔드 | content.js |
| memories source_type 'CLIP' 추가 | 백엔드 | 마이그레이션 |

**완료 기준**: Extension에서 로그인 후 원클릭 저장, 텍스트 선택 저장

---

## 12. 리스크 및 대응 방안

| 리스크 | 영향도 | 대응 방안 |
|---|---|---|
| Kakao OAuth scope 심사 지연 | 높음 | `talk_message` scope는 사전 심사 필요. 조기 신청. |
| 카카오톡 채널 사업자 인증 필요 | 높음 | 개인 채널은 기능 제한 있음. 비즈니스 채널 검토. |
| Supabase Kakao provider_token 만료 | 중간 | refresh_token 자체 갱신 로직 구현 (기존 코드 재활용) |
| 오픈빌더 스킬 서버 3초 응답 제한 | 중간 | 즉시 "저장 중" 응답 후 callbackUrl로 비동기 결과 전달 |
| botUserKey 변경 가능성 | 낮음 | 카카오 정책상 안정적이나, plusfriendUserKey 백업 매핑 유지 |
| Chrome Extension 리뷰 지연 | 중간 | 개발자 모드 사이드로딩으로 먼저 배포, 이후 스토어 등록 |

---

## 13. 참고 자료

- [Supabase Auth - Login with Kakao](https://supabase.com/docs/guides/auth/social-login/auth-kakao)
- [Supabase Auth - Identity Linking](https://supabase.com/docs/guides/auth/auth-identity-linking)
- [Kakao Developers - 카카오톡 채널 API](https://developers.kakao.com/docs/latest/ko/kakaotalk-channel/common)
- [Kakao Developers - 카카오톡 메시지 REST API](https://developers.kakao.com/docs/latest/ko/kakaotalk-message/rest-api)
- [Kakao i 오픈빌더 - 스킬 만들기](https://kakaobusiness.gitbook.io/main/tool/chatbot/skill_guide/make_skill)
- [Chrome Extension + Supabase Auth](https://pustelto.com/blog/supabase-auth/)
- [Chrome Extension OAuth with Manifest V3](https://gourav.io/blog/supabase-auth-chrome-extension)

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|---|---|---|
| v1.0 | 2026-02-10 | 초안 작성 |
