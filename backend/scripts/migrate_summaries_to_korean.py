import argparse
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = 10
ASCII_THRESHOLD = 0.80

TRANSLATE_PROMPT = (
    "다음 영어 요약을 한국어로 자연스럽게 번역하세요. "
    "핵심 논점과 결론을 포함하여 2-3문장으로 작성하세요. "
    "번역만 출력하세요.\n\n원문: {summary}"
)


def is_mostly_ascii(text: str) -> bool:
    """ASCII 비율이 임계값 이상이면 True (영어 요약으로 판정)."""
    if not text:
        return False
    ascii_count = sum(1 for c in text if ord(c) < 128)
    return (ascii_count / len(text)) >= ASCII_THRESHOLD


async def migrate(dry_run: bool = True):
    from app.config.database import get_supabase_client
    from app.config.llm import get_analytical_llm

    db = get_supabase_client()
    llm = get_analytical_llm()

    logger.info("영어 요약 → 한국어 마이그레이션 시작 (dry_run=%s)", dry_run)

    # 모든 메모리 조회
    result = db.table("memories").select("id, summary").not_.is_("summary", "null").execute()
    all_memories = result.data or []
    logger.info("전체 메모리: %d개", len(all_memories))

    # 영어 요약 필터링
    english_summaries = [m for m in all_memories if is_mostly_ascii(m.get("summary", ""))]
    logger.info("영어 요약 메모리: %d개", len(english_summaries))

    if dry_run:
        for m in english_summaries[:5]:
            logger.info("  [DRY] id=%s, summary=%s", m["id"], m["summary"][:80])
        logger.info("dry-run 모드: 실제 변환 없이 종료합니다.")
        return

    migrated = 0
    failed = 0

    for i in range(0, len(english_summaries), BATCH_SIZE):
        batch = english_summaries[i : i + BATCH_SIZE]
        logger.info(
            "배치 %d/%d 처리 중...", i // BATCH_SIZE + 1, (len(english_summaries) + BATCH_SIZE - 1) // BATCH_SIZE
        )

        for m in batch:
            try:
                from langchain_core.messages import HumanMessage

                prompt = TRANSLATE_PROMPT.format(summary=m["summary"])
                response = await llm.ainvoke([HumanMessage(content=prompt)])
                korean_summary = response.content.strip()

                if korean_summary and not is_mostly_ascii(korean_summary):
                    db.table("memories").update({"summary": korean_summary}).eq("id", m["id"]).execute()
                    migrated += 1
                    logger.info("  변환 완료: id=%s", m["id"])
                else:
                    logger.warning("  변환 실패 (여전히 영어): id=%s", m["id"])
                    failed += 1
            except Exception:
                logger.exception("  변환 오류: id=%s", m["id"])
                failed += 1

        # 배치 간 잠시 대기 (rate limit 방지)
        if i + BATCH_SIZE < len(english_summaries):
            await asyncio.sleep(1)

    logger.info("마이그레이션 완료: 성공=%d, 실패=%d", migrated, failed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="영어 메모리 요약을 한국어로 마이그레이션")
    parser.add_argument("--execute", action="store_true", help="실제 마이그레이션 실행 (기본값: dry-run)")
    args = parser.parse_args()

    asyncio.run(migrate(dry_run=not args.execute))
