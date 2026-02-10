"""
Graph Schemas
Request/Response DTOs for knowledge graph endpoints
"""

from typing import Any

from pydantic import BaseModel


class GraphNode(BaseModel):
    """Node in the knowledge graph"""

    id: str
    label: str
    properties: dict[str, Any] = {}


class GraphLink(BaseModel):
    """Link/Edge in the knowledge graph"""

    source: str
    target: str
    type: str
    properties: dict[str, Any] = {}


class GraphDataResponse(BaseModel):
    """Graph data for visualization"""

    nodes: list[GraphNode]
    links: list[GraphLink]


class EntityInput(BaseModel):
    """Entity to be saved to graph"""

    name: str
    type: str


class RelationInput(BaseModel):
    """Relation to be saved to graph"""

    source: str
    target: str
    type: str
