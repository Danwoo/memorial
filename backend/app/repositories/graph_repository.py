"""
Graph Repository
Data access layer for Neo4j knowledge graph
"""
from typing import List, Dict, Any, Optional
from langchain_community.graphs import Neo4jGraph

from app.config.settings import get_settings


class GraphRepository:
    """Repository for Neo4j graph operations"""
    
    def __init__(self, graph: Optional[Neo4jGraph] = None):
        """
        Initialize with optional Neo4j connection.
        If not provided, attempts to connect using settings.
        """
        if graph:
            self.graph = graph
        else:
            self._init_connection()
    
    def _init_connection(self):
        """Initialize Neo4j connection from settings."""
        settings = get_settings()
        
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
    
    @property
    def is_connected(self) -> bool:
        """Check if Neo4j is connected."""
        return self.graph is not None
    
    async def save_entities(
        self,
        entities: List[Dict],
        source_id: str
    ) -> None:
        """Save entities to Neo4j graph."""
        if not self.graph:
            return
        
        for entity in entities:
            label = entity.get("type", "Concept").replace(" ", "")
            name = entity.get("name")
            if not name:
                continue
            
            query = f"MERGE (e:{label} {{name: $name}})"
            self.graph.query(query, {"name": name})
        
        # Link entities to source memory
        self.graph.query(
            "MERGE (m:Memory {id: $id})",
            {"id": str(source_id)}
        )
        
        for entity in entities:
            name = entity.get("name")
            if not name:
                continue
            
            query = """
            MATCH (m:Memory {id: $id}), (e {name: $name})
            MERGE (m)-[:MENTIONS]->(e)
            """
            self.graph.query(query, {"id": str(source_id), "name": name})
    
    async def save_relations(
        self,
        relations: List[Dict]
    ) -> None:
        """Save relations to Neo4j graph."""
        if not self.graph:
            return
        
        for rel in relations:
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
    
    async def get_graph_data(self, limit: int = 100) -> Dict[str, List]:
        """
        Retrieve graph data for visualization.
        Returns nodes and links in D3 compatible format.
        """
        if not self.graph:
            return {"nodes": [], "links": []}
        
        try:
            # Query returns dicts when using LangChain Neo4jGraph
            # Use Cypher functions to extract labels and types
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

