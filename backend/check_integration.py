"""
System Integration Check Script
Verifies connections to all external services:
1. OpenAI API
2. Supabase DB (Postgres)
3. Neo4j Graph DB
"""
import asyncio
import os
from dotenv import load_dotenv

# Load env vars
load_dotenv()

async def check_integration():
    print("🔍 Starting System Integration Check...\n")
    
    # 1. OpenAI Check
    print("[1] Checking OpenAI Connection...")
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
        res = await llm.ainvoke("Hello")
        print(f"✅ OpenAI OK: {res.content}")
    except Exception as e:
        print(f"❌ OpenAI FAILED: {e}")

    # 2. Supabase DB Check
    print("\n[2] Checking Supabase DB Connection...")
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if not url or "your-project" in url:
             print("⚠️ Supabase URL not configured.")
        else:
            db = create_client(url, key)
            # Simple query
            res = db.table("memories").select("count", count="exact").execute()
            print(f"✅ Supabase OK: Connected to URL. Table 'memories' exists.")
    except Exception as e:
        print(f"❌ Supabase FAILED: {e}")

    # 3. Neo4j Check
    print("\n[3] Checking Neo4j Connection...")
    try:
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        
        if not uri:
            print("⚠️ Neo4j URI not configured.")
        else:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(uri, auth=(user, password))
            driver.verify_connectivity()
            print(f"✅ Neo4j OK: Verified connectivity to {uri}")
            driver.close()
    except Exception as e:
        print(f"❌ Neo4j FAILED: {e}")

    print("\nDone.")

if __name__ == "__main__":
    asyncio.run(check_integration())
