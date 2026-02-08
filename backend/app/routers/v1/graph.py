"""
Graph Router
API endpoints for knowledge graph visualization
"""
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from fastapi import APIRouter, HTTPException, Query, Depends

logger = logging.getLogger(__name__)

from app.services.graph_service import GraphService
from app.repositories.memory_repository import MemoryRepository
from app.dependencies import get_graph_service, get_memory_repository

router = APIRouter(prefix="/graph", tags=["graph"])


def generate_node_id(prefix: str, content: str) -> str:
    """Generate consistent node ID from content."""
    return f"{prefix}_{hashlib.md5(content.encode()).hexdigest()[:8]}"


@router.get("", response_model=Dict[str, List[Any]])
async def get_graph(
    mock: bool = Query(True),
    limit: int = Query(100, ge=1, le=500),
    graph_service: GraphService = Depends(get_graph_service),
    memory_repo: MemoryRepository = Depends(get_memory_repository)
):
    """
    Get graph data for visualization.
    Returns {nodes: [], links: []}
    
    Generates graph from actual memories showing relationships:
    - Resource <-> Concept (extracted topics)
    - Chat <-> Concept (discussed topics)
    - Resource <-> Chat (when chat references a resource)
    - Memory <-> Entity (extracted entities)
    """
    if mock:
        # Generate dynamic mock data from actual memories
        try:
            memories = await memory_repo.get_all()
            
            nodes = []
            links = []
            seen_nodes = set()
            concept_nodes = {}  # Track concepts to avoid duplicates
            
            for memory in memories[:limit]:
                memory_id = str(memory.get("id", ""))
                source_type = memory.get("source_type", "NOTE")
                title = memory.get("title", "Untitled")
                tags = memory.get("tags", []) or []
                content = memory.get("content", "")[:200]
                url = memory.get("url", "")
                created_at = memory.get("created_at", "")
                
                # Create memory node
                node_label = "Resource" if source_type in ["WEB", "PDF"] else "Memory"
                if source_type == "CHAT":
                    node_label = "Chat"
                
                if memory_id not in seen_nodes:
                    nodes.append({
                        "id": memory_id,
                        "label": node_label,
                        "name": title,
                        "url": url,
                        "properties": {
                            "title": title,
                            "summary": content,
                            "tags": tags,
                            "source_type": source_type,
                            "created_at": created_at
                        }
                    })
                    seen_nodes.add(memory_id)
                
                # Create concept nodes from tags
                for tag in tags:
                    concept_id = generate_node_id("concept", tag)
                    
                    if concept_id not in seen_nodes:
                        nodes.append({
                            "id": concept_id,
                            "label": "Concept",
                            "name": tag,
                            "properties": {"name": tag}
                        })
                        seen_nodes.add(concept_id)
                        concept_nodes[tag] = concept_id
                    
                    # Link memory to concept
                    link_type = "DISCUSSES" if node_label == "Chat" else "MENTIONS"
                    links.append({
                        "source": memory_id,
                        "target": concept_id,
                        "type": link_type
                    })
                
                # Create relationships between concepts with same tags
                for tag in tags:
                    for other_tag in tags:
                        if tag != other_tag and tag in concept_nodes and other_tag in concept_nodes:
                            link_key = tuple(sorted([concept_nodes[tag], concept_nodes[other_tag]]))
                            # Add RELATED_TO between concepts (deduplicated later)
                            links.append({
                                "source": concept_nodes[tag],
                                "target": concept_nodes[other_tag],
                                "type": "RELATED_TO"
                            })
            
            # Find Resource-Chat relationships (same tags = discussed same topic)
            resource_memories = [m for m in memories if m.get("source_type") in ["WEB", "PDF"]]
            chat_memories = [m for m in memories if m.get("source_type") == "CHAT"]
            
            for resource in resource_memories[:20]:
                resource_tags = set(resource.get("tags", []) or [])
                resource_id = str(resource.get("id", ""))
                
                for chat in chat_memories[:20]:
                    chat_tags = set(chat.get("tags", []) or [])
                    chat_id = str(chat.get("id", ""))
                    
                    # If they share tags, they're related
                    common_tags = resource_tags & chat_tags
                    if common_tags:
                        links.append({
                            "source": chat_id,
                            "target": resource_id,
                            "type": "REFERENCES"
                        })
            
            # Deduplicate links
            unique_links = []
            seen_links = set()
            for link in links:
                link_key = (link["source"], link["target"], link["type"])
                reverse_key = (link["target"], link["source"], link["type"])
                if link_key not in seen_links and reverse_key not in seen_links:
                    unique_links.append(link)
                    seen_links.add(link_key)
            
            # If no actual data, return rich demo data
            if not nodes:
                return get_demo_graph_data()
            
            return {"nodes": nodes, "links": unique_links}
            
        except Exception as e:
            logger.exception("Error generating graph from memories")
            return get_demo_graph_data()
        
    if not graph_service.is_available:
        return {"nodes": [], "links": []}
    
    try:
        data = await graph_service.get_visualization_data(limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_demo_graph_data() -> Dict[str, List[Any]]:
    """Return rich demo graph data showing Resource-Chat relationships."""
    return {
        "nodes": [
            # Resources
            {"id": "res1", "label": "Resource", "name": "Attention Is All You Need", 
             "properties": {"title": "Attention Is All You Need", "tags": ["AI", "Transformer", "NLP"]}},
            {"id": "res2", "label": "Resource", "name": "BERT: Pre-training of Deep Bidirectional Transformers",
             "properties": {"title": "BERT Paper", "tags": ["AI", "NLP", "BERT"]}},
            {"id": "res3", "label": "Resource", "name": "React 18 New Features",
             "properties": {"title": "React 18 Features", "tags": ["React", "Frontend", "Web"]}},
            
            # Chats
            {"id": "chat1", "label": "Chat", "name": "AI 프로젝트 방향 논의",
             "properties": {"title": "AI Project Discussion", "tags": ["AI", "Project"]}},
            {"id": "chat2", "label": "Chat", "name": "프론트엔드 기술 선택",
             "properties": {"title": "Frontend Tech Selection", "tags": ["React", "Frontend"]}},
            
            # Concepts (Topics)
            {"id": "concept_ai", "label": "Concept", "name": "AI",
             "properties": {"name": "AI"}},
            {"id": "concept_nlp", "label": "Concept", "name": "NLP",
             "properties": {"name": "NLP"}},
            {"id": "concept_react", "label": "Concept", "name": "React",
             "properties": {"name": "React"}},
            {"id": "concept_frontend", "label": "Concept", "name": "Frontend",
             "properties": {"name": "Frontend"}},
            {"id": "concept_transformer", "label": "Concept", "name": "Transformer",
             "properties": {"name": "Transformer"}},
            
            # Memories (Notes)
            {"id": "mem1", "label": "Memory", "name": "Transformer 학습 노트",
             "properties": {"title": "Transformer Study Notes", "tags": ["AI", "Transformer"]}},
            {"id": "mem2", "label": "Memory", "name": "React Hooks 정리",
             "properties": {"title": "React Hooks Summary", "tags": ["React", "Frontend"]}},
        ],
        "links": [
            # Resource -> Concept (MENTIONS)
            {"source": "res1", "target": "concept_ai", "type": "MENTIONS"},
            {"source": "res1", "target": "concept_transformer", "type": "MENTIONS"},
            {"source": "res1", "target": "concept_nlp", "type": "MENTIONS"},
            {"source": "res2", "target": "concept_ai", "type": "MENTIONS"},
            {"source": "res2", "target": "concept_nlp", "type": "MENTIONS"},
            {"source": "res3", "target": "concept_react", "type": "MENTIONS"},
            {"source": "res3", "target": "concept_frontend", "type": "MENTIONS"},
            
            # Chat -> Concept (DISCUSSES)
            {"source": "chat1", "target": "concept_ai", "type": "DISCUSSES"},
            {"source": "chat2", "target": "concept_react", "type": "DISCUSSES"},
            {"source": "chat2", "target": "concept_frontend", "type": "DISCUSSES"},
            
            # Chat -> Resource (REFERENCES) - The key relationship!
            {"source": "chat1", "target": "res1", "type": "REFERENCES"},
            {"source": "chat1", "target": "res2", "type": "REFERENCES"},
            {"source": "chat2", "target": "res3", "type": "REFERENCES"},
            
            # Memory -> Resource/Concept
            {"source": "mem1", "target": "res1", "type": "REFERENCES"},
            {"source": "mem1", "target": "concept_transformer", "type": "MENTIONS"},
            {"source": "mem2", "target": "res3", "type": "REFERENCES"},
            {"source": "mem2", "target": "concept_react", "type": "MENTIONS"},
            
            # Concept -> Concept (RELATED_TO)
            {"source": "concept_ai", "target": "concept_nlp", "type": "RELATED_TO"},
            {"source": "concept_ai", "target": "concept_transformer", "type": "RELATED_TO"},
            {"source": "concept_react", "target": "concept_frontend", "type": "RELATED_TO"},
        ]
    }

