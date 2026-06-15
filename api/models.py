"""
API Models - Request and response schemas
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum


class RetrievalStrategyEnum(str, Enum):
    """Retrieval strategies."""
    VECTOR = "vector"
    GRAPH = "graph"
    BM25 = "bm25"
    HYBRID = "hybrid"


# Chat Endpoints

class ChatRequest(BaseModel):
    """Chat request model."""
    question: str = Field(..., description="User question")
    strategy: RetrievalStrategyEnum = Field(
        RetrievalStrategyEnum.HYBRID,
        description="Retrieval strategy"
    )
    top_k: int = Field(5, ge=1, le=20, description="Number of documents to retrieve")
    include_reasoning: bool = Field(True, description="Include reasoning steps")
    max_context_tokens: int = Field(4000, ge=1000, le=10000)


class ChatResponse(BaseModel):
    """Chat response model."""
    answer: str
    confidence: float = Field(..., ge=0, le=1)
    sources: List[Dict] = Field(default_factory=list)
    reasoning_steps: List[str] = Field(default_factory=list)
    processing_time_ms: float
    model: str = "gemini-1.5-pro"


# Document Endpoints

class DocumentSearchRequest(BaseModel):
    """Document search request."""
    query: str = Field(..., description="Search query")
    top_k: int = Field(5, ge=1, le=20)
    strategy: RetrievalStrategyEnum = Field(RetrievalStrategyEnum.HYBRID)


class DocumentSearchResult(BaseModel):
    """Search result."""
    nomor_pasal: str
    nomor_peraturan: str
    judul_pasal: str
    judul_peraturan: str
    pasal_text: str
    score: float = Field(..., ge=0, le=1)
    strategy: str


class DocumentSearchResponse(BaseModel):
    """Search response."""
    results: List[DocumentSearchResult]
    total_results: int
    processing_time_ms: float


class IngestionRequest(BaseModel):
    """Document ingestion request."""
    file_url: Optional[str] = Field(None, description="URL to PDF file")
    content: Optional[str] = Field(None, description="Document content (text)")
    metadata: Dict = Field(default_factory=dict)


class IngestionResponse(BaseModel):
    """Ingestion response."""
    status: str
    document_id: str
    message: str


# Graph Endpoints

class GraphExploreRequest(BaseModel):
    """Graph exploration request."""
    concept: str = Field(..., description="Concept to explore")
    depth: int = Field(2, ge=1, le=5, description="Traversal depth")
    limit: int = Field(10, ge=1, le=100)


class GraphNode(BaseModel):
    """Graph node."""
    id: str
    label: str
    type: str
    properties: Dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """Graph edge."""
    source: str
    target: str
    type: str
    properties: Dict = Field(default_factory=dict)


class GraphExploreResponse(BaseModel):
    """Graph exploration response."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    center_node: str


# Statistics Endpoints

class ComponentStats(BaseModel):
    """Statistics for a component."""
    total_operations: int
    average_time_ms: float
    total_tokens: Optional[int] = None


class SystemStats(BaseModel):
    """System statistics."""
    uptime_seconds: float
    total_queries: int
    neo4j_status: str
    rag_status: str
    components: Dict[str, ComponentStats] = Field(default_factory=dict)


# Error Response

class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str
    error_code: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: str(__import__('datetime').datetime.now()))


# Batch Operations

class BatchChatRequest(BaseModel):
    """Batch chat request."""
    questions: List[str] = Field(..., min_items=1, max_items=100)
    strategy: RetrievalStrategyEnum = Field(RetrievalStrategyEnum.HYBRID)
    parallel: bool = Field(False, description="Process in parallel")


class BatchChatResponse(BaseModel):
    """Batch chat response."""
    results: List[ChatResponse]
    total_time_ms: float
    failed_count: int = 0
