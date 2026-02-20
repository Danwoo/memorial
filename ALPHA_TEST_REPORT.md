# 🔍 Memoir AI — 알파 테스터 종합 평가 리포트

**평가 일시:** 2026-02-19  
**평가 URL:** `https://frontend-three-orcin-64.vercel.app`  
**평가 방식:** 데모 + 실제 카카오 계정 (서단우/tjeksdn1@naver.com)  
**뷰포트:** 모바일(375px) + 데스크탑(1280px)

---

## 📹 전체 테스트 영상

````carousel
![모바일 데모](C:/Users/danny/.gemini/antigravity/brain/848bb1fc-471f-4596-9d9a-030fa7c46b25/initial_browse_1771504856814.webp)
<!-- slide -->
![데스크탑 데모](C:/Users/danny/.gemini/antigravity/brain/848bb1fc-471f-4596-9d9a-030fa7c46b25/desktop_exploration_1771505124860.webp)
<!-- slide -->
![채팅·기억·저널](C:/Users/danny/.gemini/antigravity/brain/848bb1fc-471f-4596-9d9a-030fa7c46b25/real_account_chat_1771507360287.webp)
<!-- slide -->
![그래프 줌인·인사이트](C:/Users/danny/.gemini/antigravity/brain/848bb1fc-471f-4596-9d9a-030fa7c46b25/graph_zoom_interact_1771508106688.webp)
<!-- slide -->
![설정 스크롤](C:/Users/danny/.gemini/antigravity/brain/848bb1fc-471f-4596-9d9a-030fa7c46b25/settings_deep_test_1771508394429.webp)
<!-- slide -->
![RAG 대화 테스트](C:/Users/danny/.gemini/antigravity/brain/848bb1fc-471f-4596-9d9a-030fa7c46b25/chat_rag_test_1_1771508724459.webp)
<!-- slide -->
![기억 추가·검색·저널 쓰기](C:/Users/danny/.gemini/antigravity/brain/848bb1fc-471f-4596-9d9a-030fa7c46b25/memory_journal_test_1771508938195.webp)
````

---

## 🏆 총평: **7.5 / 10**

> **실제로 써보면 진가가 드러나는 서비스.** AI가 저장된 기억을 정확히 참조해서 대화하는 품질은 인상적이고, 저널 회고와 그래프 인사이트도 깊이가 있다. 하지만 **기억 검색이 아예 작동하지 않는 버그**와 초기 진입 장벽이 서비스의 발목을 잡고 있다.

---

## 🧪 A. 직접 사용 테스트 결과

### 1️⃣ Chat RAG 품질 — ⭐ **9/10** (핵심 강점)

3개의 대화를 나눠보고 AI 응답을 직접 읽었습니다.

#### 테스트 ① 추천 질문 ("최근 관심사에 대해 이야기해줘")

![AI가 GDP 1.8%, 2.1% 등 구체적 수치를 인용하면서 건강과 경제 두 관심사를 정리](C:/Users/danny/.gemini/antigravity/brain/848bb1fc-471f-4596-9d9a-030fa7c46b25/.system_generated/click_feedback/click_feedback_1771508814596.png)

**AI 응답 (요약):**
> "최근 저장하신 기억들을 살펴보면, 특히 **건강**과 **경제**에 대한 관심이 두드러지네요. 2026년 2월 19일에 저장하신 '한국 경제 전망'에서는 한국은행이 **1.8%**, OECD와 금융연구원이 **2.1%** 성장률을 전망하고 있다는 내용을 다루셨습니다. 또한, 같은 날 저장하신 건강 관련 글에서는 수면 과학에 대한 최신 연구를 언급하셨는데, AI가 수면 데이터를 통해 **130가지 질병**을 예측할 수 있다는 점이 흥미롭습니다."

✅ **구체적 수치 인용** (1.8%, 2.1%, 130가지 질병)  
✅ **저장 날짜까지 정확히 참조** (2026-02-19)  
✅ **교차 주제 연결** (건강↔경제 두 분야 동시 파악)  
✅ **자연스러운 후속 질문** ("이 두 가지 주제가 서로 연결될 수 있는 부분이 있을 것 같은데, 어떻게 생각하시나요?")

#### 테스트 ② 후속 질문 ("Explain more about the AI sleep research please.")

![AI가 이전 대화 맥락을 유지하면서 수면 연구에 대해 상세 설명](C:/Users/danny/.gemini/antigravity/brain/848bb1fc-471f-4596-9d9a-030fa7c46b25/.system_generated/click_feedback/click_feedback_1771508839113.png)

**AI 응답 (요약):**
> "You mentioned in your journal on February 19, 2026, that you found the latest research on sleep science interesting, particularly the aspect where **AI can predict 130 diseases solely based on sleep data**. AI algorithms can process vast amounts of data from sleep studies, wearable devices, or sleep tracking apps to identify correlations between sleep metrics and health outcomes."

✅ **이전 턴 맥락 완벽 유지** — 한 번의 대화에서 수면 주제를 이어받음  
✅ **영어 질문에 영어 응답** — 다국어 대응 정상  
✅ **구체적 확장** — 웨어러블, 심혈관, 당뇨, 정신건강까지 연결  
✅ **사고 유도 질문** — 윤리적 고려사항까지 물어봄

#### 테스트 ③ 교차 도메인 질문 (건강 + AI 연결)

> AI가 4가지 관점(개인 건강 관리, 예방 의학, 연구 데이터 분석, 접근성)으로 구조화해서 **한국어**로 답변 — 단순 기억 나열이 아닌 **종합적 사고** 수행

> [!NOTE]
> **RAG 판정: 생산 수준(Production-grade).** 저장된 기억의 구체적 숫자, 날짜, 주제를 정확히 참조하면서 교차 도메인 사고까지 수행. 일반 ChatGPT와의 차별점이 명확하게 느껴짐.

---

### 2️⃣ 기억 검색 (Memory Search) — 🔴 **2/10** (치명적 버그)

![memory_search_sleep_result](C:/Users/danny/.gemini/antigravity/brain/848bb1fc-471f-4596-9d9a-030fa7c46b25/memory_search_sleep_result_1771508979076.png)

- **테스트:** "sleep" 검색
- **결과:** "관련 기억을 찾지 못했습니다" — **빈 결과**
- **모순:** "전체" 탭에는 "New drug resets the body clock and cuts jet lag recovery nearly in half" 등 sleep 관련 기억이 **최소 3개** 존재
- **심각도:** 검색은 서비스의 핵심 기능인데 **아예 작동하지 않음**

> [!CAUTION]
> 이것은 단순 UX 이슈가 아니라 **기능 장애**입니다. 벡터 검색(pgvector) 또는 검색 인덱스에 문제가 있을 가능성이 높습니다. AI 대화(RAG)에서는 기억을 잘 찾는 걸 보면, 기억 페이지의 검색과 RAG 검색이 서로 다른 파이프라인을 사용하는 것으로 보이며 전자에 문제가 있습니다.

---

### 3️⃣ 기억 추가 (Add Memory via URL) — ✅ **9/10**

![URL 입력 모달 — news.ycombinator.com 입력](C:/Users/danny/.gemini/antigravity/brain/848bb1fc-471f-4596-9d9a-030fa7c46b25/.system_generated/click_feedback/click_feedback_1771508999120.png)

- `https://news.ycombinator.com` 입력 → 즉시 저장 완료
- "Hacker News"로 자동 타이틀 추출
- "방금 전" 타임스탬프로 목록에 즉시 반영
- 기억 수 16 → **17개**로 자동 업데이트

✅ 모달 UI 깔끔 (웹 URL / 메모 / PDF 3탭)  
✅ 스크래핑 파이프라인 정상 작동  
✅ 리스트 실시간 갱신

---

### 4️⃣ 저널 작성 — ✅ **8/10**

![저널 좌측 메모리 사이드바](C:/Users/danny/.gemini/antigravity/brain/848bb1fc-471f-4596-9d9a-030fa7c46b25/journal_test_typing_1771509058335.png)

- 리치텍스트 에디터 정상 동작 (텍스트 입력 확인)
- 좌측 사이드바에 오늘의 메모리 목록(WEB/NOTE 카드) + AI 액션(하루 정리, 세션 기반 초안) 표시
- "AI 분석 시작" 버튼으로 수동 트리거 가능
- 우측 패널에 성찰 질문 / 마음 건강 탭 존재

---

### 5️⃣ 채팅 히스토리 — ✅ **8/10**

![채팅 히스토리 목록](C:/Users/danny/.gemini/antigravity/brain/848bb1fc-471f-4596-9d9a-030fa7c46b25/.system_generated/click_feedback/click_feedback_1771509113530.png)

- 좌측 사이드바에 **6개+ 과거 대화** 목록 표시
- 제목 자동 생성: "건강과 경제 관심사", "수면 과학", "효과적인 건강 관리 방법" 등
- 클릭하면 이전 대화 정상 로딩 — **기억이 16→17개로 실시간 반영됨** (HN URL 추가 반영)
- 추천 질문 2개와 트렌딩 태그(#AI, #한국은행, #Circadian Rhythm) 표시

---

## 📊 B. 페이지별 평가 요약

| 페이지 | 점수 | 핵심 |
|--------|------|------|
| **대화(Chat)** | 9/10 ⭐ | RAG 품질 최고, 구체적 수치·날짜 참조, 교차 사고 |
| **기억(Memories)** | 7/10 | 카드·모달·필터 우수, **검색 완전 불량** |
| **저널(Journal)** | 8/10 ⭐ | 3-panel, 회고질문, 템플릿, AI분석 |
| **그래프(Graph)** | 7/10 | 줌인 시 라벨, 노드 패널, AI 클러스터 인사이트 |
| **대시보드** | 7/10 | 개인화 통계, 히트맵, AI 발견 |
| **설정** | 7.5/10 | 데이터 내보내기, 스마트 알림, 멀티 소셜 |

---

## 🔴 C. 이슈 우선순위

### Critical (즉시 수정)

| # | 이슈 | 근거 |
|---|------|------|
| 1 | **기억 검색 "sleep" 결과 없음** | 핵심 기능 완전 장애. 벡터 검색 파이프라인 점검 필요 |
| 2 | 채팅 메시지 `max-width` 미설정 | 데스크탑에서 메시지가 전체 너비 차지 → 가독성 저하 |

### Major

| # | 이슈 |
|---|------|
| 3 | 그래프 초기 줌에서 라벨 없음 → "빈 점 나열" 첫인상 |
| 4 | AI 응답 8-10초 (간단 인사에도) |
| 5 | 대시보드 초기 빈 화면 (스켈레톤 필요) |
| 6 | 모바일 사이드바 배경 겹침 |

### Minor

| # | 이슈 |
|---|------|
| 7 | 글로우 효과 올드함 |
| 8 | 데모 태그 뭉침 |

---

## 💡 D. 최종 인사이트

**가장 강력한 점:**
- RAG 대화 품질이 생산 수준 — 저장 기억의 구체적 수치/날짜를 참조하며 교차 사고 수행
- URL 스크래핑 파이프라인이 빠르고 안정적
- 저널 회고질문 + 그래프 AI 인사이트의 조합

**가장 치명적인 점:**
- 기억 검색이 **완전히** 작동하지 않음 (RAG와 기억 검색이 다른 파이프라인 사용 추정)

**가장 아쉬운 점:**
- 이 좋은 기능들이 **표면에 드러나지 않음** — 그래프는 줌인해야, 설정은 스크롤해야, 채팅은 보내봐야 가치를 알 수 있음
- 10분짜리 CSS 수정(채팅 max-width, 글로우 제거 등)으로 첫인상이 크게 개선될 수 있음
