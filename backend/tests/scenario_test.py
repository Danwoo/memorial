"""사용자 관점 멀티턴 시나리오 테스트 (실제 LLM 호출)."""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

USER_ID = "11111111-1111-1111-1111-111111111111"
SESSION_ID = "22222222-2222-2222-2222-222222222222"
SEP = "=" * 60

# ──────────────────────────────────────────────
# 실제 사용자 데이터 시뮬레이션
# ──────────────────────────────────────────────
MOCK_SCRAPS = [
    {
        "id": "scrap-001",
        "title": "번아웃을 극복하는 5가지 방법",
        "content": (
            "번아웃은 만성 스트레스로 인한 신체적, 정서적 고갈 상태다. "
            "극복하려면: 1) 업무 경계 설정 — 퇴근 후 슬랙 알림 끄기, "
            "2) 작은 성취 기록 — 매일 완료한 일 3가지 적기, "
            "3) 신체 활동 — 30분 걷기도 충분, "
            "4) 사회적 연결 유지 — 친구와 짧은 통화, "
            "5) 완벽주의 내려놓기 — 80% 완성도로 출시하고 피드백 받기."
        ),
        "source_url": "https://hbr.org/burnout-recovery",
        "tags": ["번아웃", "멘탈헬스", "생산성"],
        "created_at": "2026-02-20T10:00:00",
        "score": 0.91,
    },
    {
        "id": "scrap-002",
        "title": "딥워크: 집중력의 기술",
        "content": (
            "칼 뉴포트의 딥워크 원칙. 얕은 작업(이메일, 슬랙)을 하루 2시간 이내로 제한하고, "
            "나머지 시간은 방해 없는 깊은 집중 작업에 투자한다. "
            "집중 세션은 90분 단위로, 완전한 휴식을 사이에 넣는다. "
            "스마트폰은 다른 방에 둔다."
        ),
        "source_url": "https://calnewport.com/deep-work",
        "tags": ["집중력", "생산성", "딥워크"],
        "created_at": "2026-02-22T14:30:00",
        "score": 0.85,
    },
    {
        "id": "scrap-003",
        "title": "React useCallback, useMemo 언제 써야 하나",
        "content": (
            "useCallback은 함수 참조를 메모이제이션하고, useMemo는 값을 메모이제이션한다. "
            "둘 다 렌더링 최적화용이지만 남용하면 오히려 성능이 나빠진다. "
            "규칙: 1) 자식 컴포넌트에 props로 넘기는 함수에는 useCallback, "
            "2) 계산 비용이 큰 값에는 useMemo, 3) 단순 원시값에는 쓰지 말 것."
        ),
        "tags": ["React", "프론트엔드", "성능최적화"],
        "created_at": "2026-02-24T09:00:00",
        "score": 0.78,
    },
]

MOCK_DIARIES = [
    {
        "id": "diary-001",
        "content": (
            "오늘 팀 앞에서 스프린트 발표를 했는데 완전히 망쳤다. "
            "질문에 제대로 답을 못하고 말이 꼬였다. "
            "준비를 충분히 했다고 생각했는데 막상 앞에 서니까 머리가 하얘졌다. "
            "너무 창피하고 자책이 심하다. 동료들이 어떻게 볼지 신경 쓰인다."
        ),
        "mood": "우울",
        "tags": ["발표", "자책", "실패"],
        "created_at": "2026-02-25T22:00:00",
    },
    {
        "id": "diary-002",
        "content": (
            "요즘 계속 피곤하다. 퇴근하고 나면 아무것도 하기 싫다. "
            "코딩도 예전만큼 재밌지 않다. 번아웃인가 싶기도 하고. "
            "주말에도 일 생각이 자꾸 난다."
        ),
        "mood": "무기력",
        "tags": ["번아웃", "피로", "무기력"],
        "created_at": "2026-02-26T21:30:00",
    },
]


def make_context():
    ctx = MagicMock()
    ctx.hybrid_search = MagicMock()
    ctx.hybrid_search.search = AsyncMock(return_value=MOCK_SCRAPS)
    ctx.vector_repo = MagicMock()
    ctx.vector_repo.similarity_search = AsyncMock(return_value=MOCK_SCRAPS[:2])
    ctx.diary_repo = MagicMock()
    ctx.diary_repo.get_diaries = AsyncMock(return_value=MOCK_DIARIES)
    ctx.diary_repo.get_diaries_by_date_range = AsyncMock(return_value=MOCK_DIARIES)
    ctx.socrates_repo = MagicMock()
    ctx.socrates_repo.get_previous_sessions = AsyncMock(return_value=[])
    ctx.socrates_repo.get_recent_session_summaries = AsyncMock(return_value=[])
    ctx.socrates_repo.get_sessions_by_topic = AsyncMock(return_value=[])
    ctx.community_summary = MagicMock()
    ctx.community_summary.get_community_summaries = AsyncMock(
        return_value=[
            {
                "summary": "사용자는 번아웃과 생산성에 관심이 많은 프론트엔드 개발자",
                "entities": ["번아웃", "생산성", "React"],
            }
        ]
    )
    return ctx


cfg = {"configurable": {"thread_id": SESSION_ID}, "recursion_limit": 25}


async def scenario_socrates():
    """Socrates: 발표 실패 후 감정 대화 3턴."""
    from app.agents.socrates.graph import socrates_diary_graph
    from app.agents.socrates.state import build_socrates_initial_state
    from app.config.llm import get_streaming_llm

    llm = get_streaming_llm()
    ctx = make_context()

    print(SEP)
    print("[SCENARIO 1] Socrates — 발표 실패 후 감정 대화 (3턴)")
    print(SEP)

    # 턴 1
    q1 = "오늘 발표 완전 망했어. 너무 창피해서 팀원들 얼굴을 못 보겠어"
    conv = [HumanMessage(content=q1)]
    s = build_socrates_initial_state(messages=conv, user_id=USER_ID, session_id=SESSION_ID, user_query=q1, turn_count=1)
    r = await socrates_diary_graph.ainvoke(s, config=cfg, context=ctx)
    a1 = await llm.ainvoke(r["llm_messages"])
    print(f"[계획] plan={r['retrieval_plan']} | diary_ctx={bool(r.get('diary_context'))}")
    print(f"User  : {q1}")
    print(f"Socrates: {a1.content}\n")

    # 턴 2
    q2 = "준비는 엄청 많이 했는데 막상 서면 머리가 하얘져. 나는 왜 이럴까"
    conv += [AIMessage(content=a1.content), HumanMessage(content=q2)]
    s2 = build_socrates_initial_state(
        messages=conv, user_id=USER_ID, session_id=SESSION_ID, user_query=q2, turn_count=2
    )
    r2 = await socrates_diary_graph.ainvoke(s2, config=cfg, context=ctx)
    a2 = await llm.ainvoke(r2["llm_messages"])
    print(f"[계획] plan={r2['retrieval_plan']} | rewritten={r2['rewritten_queries']}")
    print(f"User  : {q2}")
    print(f"Socrates: {a2.content}\n")

    # 턴 3
    q3 = "요즘 번아웃도 오고 자신감도 많이 없어졌어. 어떻게 하면 좋을까"
    conv += [AIMessage(content=a2.content), HumanMessage(content=q3)]
    s3 = build_socrates_initial_state(
        messages=conv, user_id=USER_ID, session_id=SESSION_ID, user_query=q3, turn_count=3
    )
    r3 = await socrates_diary_graph.ainvoke(s3, config=cfg, context=ctx)
    a3 = await llm.ainvoke(r3["llm_messages"])
    print(f"[계획] plan={r3['retrieval_plan']} | refs={len(r3['references'])}개")
    print(f"User  : {q3}")
    print(f"Socrates: {a3.content}\n")


async def scenario_librarian():
    """Librarian: 스크랩 기반 Q&A 2턴."""
    from app.agents.librarian.graph import librarian_chat_graph
    from app.agents.librarian.state import build_librarian_chat_initial_state
    from app.config.llm import get_streaming_llm

    llm = get_streaming_llm()
    ctx = make_context()

    print(SEP)
    print("[SCENARIO 2] Librarian — 스크랩 기반 Q&A (2턴)")
    print(SEP)

    # 턴 1
    q1 = "내가 저장한 번아웃 관련 스크랩 내용 정리해줘"
    conv = [HumanMessage(content=q1)]
    s = build_librarian_chat_initial_state(
        messages=conv, user_id=USER_ID, session_id=SESSION_ID, user_query=q1, turn_count=1
    )
    r = await librarian_chat_graph.ainvoke(s, config=cfg, context=ctx)
    a1 = await llm.ainvoke(r["llm_messages"])
    print(f"[계획] plan={r['retrieval_plan']} | 검색된 스크랩={len(r['graded_memories'])}개")
    print(f"User  : {q1}")
    print(f"Librarian: {a1.content}\n")

    # 턴 2
    q2 = "딥워크랑 번아웃 극복이 어떻게 연결돼? 내 스크랩 기반으로 설명해줘"
    conv += [AIMessage(content=a1.content), HumanMessage(content=q2)]
    s2 = build_librarian_chat_initial_state(
        messages=conv, user_id=USER_ID, session_id=SESSION_ID, user_query=q2, turn_count=2
    )
    r2 = await librarian_chat_graph.ainvoke(s2, config=cfg, context=ctx)
    a2 = await llm.ainvoke(r2["llm_messages"])
    print(f"[계획] rewritten={r2['rewritten_queries']}")
    print(f"User  : {q2}")
    print(f"Librarian: {a2.content}\n")


async def scenario_oracle():
    """Oracle: 마인드맵 컨텍스트 + 일반 Q&A."""
    from app.agents.oracle.graph import oracle_graph
    from app.agents.oracle.state import build_oracle_initial_state
    from app.config.llm import get_streaming_llm

    llm = get_streaming_llm()
    ctx = make_context()

    print(SEP)
    print("[SCENARIO 3] Oracle — 마인드맵 컨텍스트 Q&A")
    print(SEP)

    q1 = "내 마인드맵에서 번아웃 노드랑 연결된 개념들 어떻게 연결돼 있는지 설명해줘"
    conv = [HumanMessage(content=q1)]
    s = build_oracle_initial_state(
        messages=conv,
        user_id=USER_ID,
        session_id=SESSION_ID,
        user_query=q1,
        turn_count=1,
        source_context={
            "type": "graph",
            "node_name": "번아웃",
            "connected_nodes": ["딥워크", "생산성", "멘탈헬스", "집중력"],
            "description": "번아웃 노드 — 4개 연결 노드 탐색 중",
        },
    )
    r = await oracle_graph.ainvoke(s, config=cfg, context=ctx)
    a1 = await llm.ainvoke(r["llm_messages"])
    print(f"[계획] plan={r['retrieval_plan']}")
    print(f"User  : {q1}")
    print(f"Oracle: {a1.content}\n")

    # 2턴: 실용적 조언 요청
    q2 = "그러면 지금 당장 번아웃에서 벗어나려면 뭐부터 해야 해?"
    conv += [AIMessage(content=a1.content), HumanMessage(content=q2)]
    s2 = build_oracle_initial_state(messages=conv, user_id=USER_ID, session_id=SESSION_ID, user_query=q2, turn_count=2)
    r2 = await oracle_graph.ainvoke(s2, config=cfg, context=ctx)
    a2 = await llm.ainvoke(r2["llm_messages"])
    print(f"[계획] plan={r2['retrieval_plan']} | refs={len(r2['references'])}개")
    print(f"User  : {q2}")
    print(f"Oracle: {a2.content}\n")


async def main():
    await scenario_socrates()
    await scenario_librarian()
    await scenario_oracle()
    print(SEP)
    print("전체 시나리오 완료")
    print(SEP)


if __name__ == "__main__":
    asyncio.run(main())
