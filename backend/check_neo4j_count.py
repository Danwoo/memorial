import asyncio
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD")

print(f"Connecting to Neo4j... {uri}")

async def main():
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        print("✅ Neo4j Connection Successful!")
        
        records, summary, keys = driver.execute_query("MATCH (n) RETURN count(n) AS count")
        count = records[0]["count"]
        print(f"📊 Current Node Count: {count}")
        
        if count == 0:
            print("👉 Graph is empty. Use Chrome Extension to save pages!")
        else:
            print("👉 Graph has data. It should show up in Frontend.")
            
        driver.close()
    except Exception as e:
        print(f"❌ Neo4j Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
