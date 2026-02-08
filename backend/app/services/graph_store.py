"""
Graph Store Service (Neo4j)
Handles creation of nodes and relationships from Ontologist's output.
"""
from typing import List, Dict, Any, Optional
from langchain_community.graphs import Neo4jGraph
from app.core.config import get_settings

class GraphStore:
    def __init__(self):
        settings = get_settings()
        
        # Check if Neo4j is configured
        if not settings.NEO4J_URI or not settings.NEO4J_PASSWORD:
            self.graph = None
            print("WARNING: Neo4j not configured. Graph features disabled.")
            return

        try:
            self.graph = Neo4jGraph(
                url=settings.NEO4J_URI,
                username=settings.NEO4J_USER or "neo4j",
                password=settings.NEO4J_PASSWORD
            )
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            self.graph = None

    async def save_graph_documents(
        self, 
        entities: List[Dict], 
        relations: List[Dict],
        source_id: str
    ):
        """
        Save entities and relations to Neo4j.
        Associates them with the source memory_id.
        """
        if not self.graph:
            return

        # Prepare Cypher queries
        # 1. Merge Entities
        for entity in entities:
            # entity: {name: "React", type: "Technology"}
            label = entity.get("type", "Concept").replace(" ", "")
            name = entity.get("name")
            if not name:
                continue
                
            query = f"""
            MERGE (e:{label} {{name: $name}})
            """
            self.graph.query(query, {"name": name})

        # 2. Merge Relations
        for rel in relations:
            # rel: {source: "React", target: "Frontend", type: "USED_FOR"}
            source = rel.get("source")
            target = rel.get("target")
            rel_type = rel.get("type", "RELATED_TO").upper().replace(" ", "_")
            
            if not source or not target:
                continue
                
            query = f"""
            MATCH (a {{name: $source}}), (b {{name: $target}})
            MERGE (a)-[:{rel_type}]->(b)
            """
            self.graph.query(query, {"source": source, "target": target})
            
        # 3. Link to Source Memory (Optional but good for lineage)
        # Create Memory Node
        self.graph.query(
            "MERGE (m:Memory {id: $id})", 
            {"id": str(source_id)}
        )
        
        # Link Entities to Memory
        for entity in entities:
             name = entity.get("name")
             if not name: continue
             
             query = f"""
             MATCH (m:Memory {{id: $id}}), (e {{name: $name}})
             MERGE (m)-[:MENTIONS]->(e)
             """
             self.graph.query(query, {"id": str(source_id), "name": name})

    async def get_graph_data(self, limit: int = 100) -> Dict[str, List]:
        """
        Retrieve graph data for visualization.
        Returns nodes and links in D3 compatible format.
        """
        if not self.graph:
            return {"nodes": [], "links": []}
        
        try:
            # Query returns dicts when using LangChain Neo4jGraph
            query = f"""
            MATCH (n)-[r]->(m)
            RETURN 
                n.name as source_name, 
                n.id as source_id,
                labels(n)[0] as source_label,
                m.name as target_name,
                m.id as target_id,
                labels(m)[0] as target_label,
                type(r) as rel_type
            LIMIT {limit}
            """
            results = self.graph.query(query)
            
            nodes = {}
            links = []
            
            for record in results:
                # Process Source Node
                source_id = record.get('source_id') or record.get('source_name')
                if source_id and source_id not in nodes:
                    nodes[source_id] = {
                        "id": source_id,
                        "label": record.get('source_label', 'Unknown'),
                        "name": record.get('source_name', source_id)
                    }
                    
                # Process Target Node
                target_id = record.get('target_id') or record.get('target_name')
                if target_id and target_id not in nodes:
                    nodes[target_id] = {
                        "id": target_id,
                        "label": record.get('target_label', 'Unknown'),
                        "name": record.get('target_name', target_id)
                    }
                
                # Process Link
                if source_id and target_id:
                    links.append({
                        "source": source_id,
                        "target": target_id,
                        "type": record.get('rel_type', 'RELATED_TO')
                    })
                    
            return {
                "nodes": list(nodes.values()),
                "links": links
            }
        except Exception as e:
            print(f"Error fetching graph data: {e}")
            return {"nodes": [], "links": []}

# Singleton instance
graph_store = GraphStore()
