import sys
import os
import asyncio

# Ensure backend directory is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.insert(0, backend_dir)

print(f"DEBUG: Backend Dir: {backend_dir}")

try:
    from app.agents.librarian.nodes.curator import curator_node
    print("DEBUG: Import Successful")
except Exception as e:
    print(f"DEBUG: Import Failed: {e}")
    sys.exit(1)

async def test_curator_url():
    print("Running Curator URL Test...")
    
    test_url = "https://www.example.com" 
    
    state = {
        "target_text": test_url,
        "target_memory_id": "00000000-0000-0000-0000-000000000000"
    }
    
    try:
        result = await curator_node(state)
        
        print("\n=== Result ===")
        print(f"Classification: {result.get('classification')}")
        print(f"Tags: {result.get('tags')}")
        print(f"Summary: {result.get('summary')}")
        
        if state.get("source_url") == test_url:
            print("\n[SUCCESS] Source URL captured in state")
        else:
            print(f"\n[FAIL] Source URL missing or mismatch: {state.get('source_url')}")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_curator_url())
