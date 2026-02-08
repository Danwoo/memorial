import asyncio
import sys
sys.path.insert(0, '.')

from app.repositories.journal_repository import JournalRepository

async def test_journal():
    repo = JournalRepository()
    try:
        result = await repo.create_journal(
            user_id=None,
            content="Direct test from script",
            mood="NEUTRAL"
        )
        print("SUCCESS!")
        print(result)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_journal())
