"""
Graph Schemas
Request/Response DTOs for knowledge graph endpoints
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class GraphNode(BaseModel):
    """Node in the knowledge graph"""
    id: str
    label: str
    properties: Dict[str, Any] = {}


class GraphLink(BaseModel):
    """Link/Edge in the knowledge graph"""
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = {}


class GraphDataResponse(BaseModel):
    """Graph data for visualization"""
    nodes: List[GraphNode]
    links: List[GraphLink]


class EntityInput(BaseModel):
    """Entity to be saved to graph"""
    name: str
    type: str


class RelationInput(BaseModel):
    """Relation to be saved to graph"""
    source: str
    target: str
    type: str
