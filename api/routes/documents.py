"""
Documents Routes - Search and Ingestion
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging
import time

from api.models import (
    DocumentSearchRequest, DocumentSearchResponse, DocumentSearchResult,
    IngestionRequest, IngestionResponse, ErrorResponse
)
from api.main import app_state
from rag.retriever import RetrievalStrategy


logger = logging.getLogger("legalkg.api.documents")
router = APIRouter()


def get_neo4j():
    """Get Neo4j client."""
    if not app_state["neo4j_client"]:
        raise HTTPException(
            status_code=503,
            detail="Neo4j connection not available"
        )
    return app_state["neo4j_client"]


def get_retriever():
    """Get retriever."""
    retriever = app_state.get("retriever")
    if not retriever and app_state["neo4j_client"]:
        from rag.retriever import MultiStrategyRetriever
        retriever = MultiStrategyRetriever(app_state["neo4j_client"], app_state["vector_manager"])
        app_state["retriever"] = retriever
    
    if not retriever:
        raise HTTPException(
            status_code=503,
            detail="Retriever not available"
        )
    return retriever


@router.post("/search", response_model=DocumentSearchResponse, responses={503: {"model": ErrorResponse}})
async def search_documents(request: DocumentSearchRequest, retriever = Depends(get_retriever)):
    """
    Search for documents.
    
    - **query**: Search query
    - **top_k**: Number of results to return (1-20)
    - **strategy**: Retrieval strategy (vector, graph, bm25, hybrid)
    """
    try:
        logger.info(f"Document search: {request.query[:50]}...")
        
        start_time = time.time()
        
        # Convert strategy
        strategy_map = {
            "vector": RetrievalStrategy.VECTOR,
            "graph": RetrievalStrategy.GRAPH,
            "bm25": RetrievalStrategy.BM25,
            "hybrid": RetrievalStrategy.HYBRID,
        }
        
        strategy = strategy_map.get(request.strategy.value, RetrievalStrategy.HYBRID)
        
        # Retrieve documents
        documents, stats = retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            strategy=strategy,
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        # Convert to response format
        results = [
            DocumentSearchResult(
                nomor_pasal=doc.nomor_pasal,
                nomor_peraturan=doc.nomor_peraturan,
                judul_pasal=doc.judul_pasal,
                judul_peraturan=doc.judul_peraturan,
                pasal_text=doc.pasal_text[:500] + "..." if len(doc.pasal_text) > 500 else doc.pasal_text,
                score=doc.score,
                strategy=doc.strategy.value,
            )
            for doc in documents
        ]
        
        return DocumentSearchResponse(
            results=results,
            total_results=len(results),
            processing_time_ms=processing_time,
        )
        
    except Exception as e:
        logger.error(f"Document search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/pasal/{nomor}", tags=["documents"])
async def get_pasal(nomor: str, neo4j_client = Depends(get_neo4j)):
    """
    Get a specific pasal by number.
    
    - **nomor**: Pasal number
    """
    try:
        query = """
        MATCH (p:Pasal {nomor: $nomor})
        OPTIONAL MATCH (p)-[:BAGIAN_DARI]->(per:Peraturan)
        RETURN p.nomor as nomor, p.judul as judul, p.full_text as text,
               per.nomor as peraturan_nomor, per.judul as peraturan_judul
        """
        
        result = neo4j_client.execute_query(query, nomor=nomor)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Pasal {nomor} not found"
            )
        
        pasal = result[0]
        
        return {
            "nomor": pasal.get("nomor"),
            "judul": pasal.get("judul"),
            "text": pasal.get("text"),
            "peraturan": {
                "nomor": pasal.get("peraturan_nomor"),
                "judul": pasal.get("peraturan_judul"),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get pasal failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve pasal: {str(e)}"
        )


@router.get("/peraturan", tags=["documents"])
async def list_peraturan(skip: int = 0, limit: int = 10, neo4j_client = Depends(get_neo4j)):
    """
    List all regulations.
    
    - **skip**: Number of records to skip
    - **limit**: Maximum records to return (1-100)
    """
    try:
        limit = min(limit, 100)
        
        query = """
        MATCH (p:Peraturan)
        RETURN p.nomor as nomor, p.judul as judul, p.tahun as tahun,
               p.jenis as jenis, p.total_pasal as total_pasal
        ORDER BY p.tahun DESC
        SKIP $skip
        LIMIT $limit
        """
        
        results = neo4j_client.execute_query(query, skip=skip, limit=limit)
        
        # Get total count
        count_query = "MATCH (p:Peraturan) RETURN COUNT(p) as count"
        count_result = neo4j_client.execute_query(count_query)
        total = count_result[0].get("count", 0) if count_result else 0
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "results": [
                {
                    "nomor": r.get("nomor"),
                    "judul": r.get("judul"),
                    "tahun": r.get("tahun"),
                    "jenis": r.get("jenis"),
                    "total_pasal": r.get("total_pasal"),
                }
                for r in results
            ]
        }
        
    except Exception as e:
        logger.error(f"List peraturan failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list regulations: {str(e)}"
        )


@router.post("/ingest", response_model=IngestionResponse, responses={503: {"model": ErrorResponse}})
async def ingest_document(request: IngestionRequest):
    """
    Ingest a new document.
    
    Currently a placeholder - in production would:
    - Download PDF from URL
    - Extract text
    - Run through TAHAP 1 pipeline
    - Index in graph
    """
    try:
        logger.info("Document ingestion started")
        
        # Placeholder implementation
        return IngestionResponse(
            status="queued",
            document_id="doc_123",
            message="Document queued for processing. Check status with GET /documents/ingest/{document_id}"
        )
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )


@router.get("/ingest/{document_id}", tags=["documents"])
async def get_ingest_status(document_id: str):
    """Get document ingestion status."""
    return {
        "document_id": document_id,
        "status": "completed",
        "message": "Placeholder implementation"
    }
