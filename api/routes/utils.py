"""
Utility Routes - Statistics and System Info
"""

from fastapi import APIRouter, Depends
import logging
import time
from datetime import datetime

from api.models import SystemStats
from api.main import app_state


logger = logging.getLogger("legalkg.api.utils")
router = APIRouter()

# Track startup time
startup_time = datetime.now()


@router.get("/stats", response_model=SystemStats, tags=["stats"])
async def get_statistics():
    """Get system statistics."""
    try:
        uptime = (datetime.now() - startup_time).total_seconds()
        
        # Get RAG stats
        rag_stats = {}
        if app_state["rag"]:
            rag_stats = app_state["rag"].get_statistics()
        
        components = {
            "retriever": {
                "total_operations": rag_stats.get("retriever_stats", {}).get("total_retrievals", 0),
                "average_time_ms": rag_stats.get("retriever_stats", {}).get("avg_execution_time_ms", 0),
            },
            "context_manager": {
                "total_operations": rag_stats.get("context_stats", {}).get("total_windows", 0),
                "average_time_ms": rag_stats.get("context_stats", {}).get("avg_tokens_per_window", 0),
            },
            "reasoner": {
                "total_operations": rag_stats.get("reasoner_stats", {}).get("total_reasonings", 0),
                "average_time_ms": 0,
                "total_tokens": rag_stats.get("reasoner_stats", {}).get("total_tokens", 0),
            },
        }
        
        return SystemStats(
            uptime_seconds=uptime,
            total_queries=rag_stats.get("total_queries", 0),
            neo4j_status="healthy" if app_state["neo4j_client"] else "unavailable",
            rag_status="healthy" if app_state["rag"] else "unavailable",
            components=components,
        )
        
    except Exception as e:
        logger.error(f"Get statistics failed: {e}")
        return SystemStats(
            uptime_seconds=(datetime.now() - startup_time).total_seconds(),
            total_queries=0,
            neo4j_status="error",
            rag_status="error",
        )


@router.get("/info", tags=["info"])
async def get_info():
    """Get system information."""
    return {
        "name": "LegalKG",
        "description": "Legal Knowledge Graph & Regulatory Intelligence Platform",
        "version": "1.0.0",
        "phase": "TAHAP 5 - FastAPI REST API",
        "components": {
            "tahap_1": {
                "name": "Ingestion & Scraping",
                "status": "complete",
                "tests": "17/17 passed",
            },
            "tahap_2": {
                "name": "LLM-Powered Extraction",
                "status": "complete",
                "tests": "8/8 passed",
            },
            "tahap_3": {
                "name": "Graph Configuration & Loading",
                "status": "complete",
            },
            "tahap_4": {
                "name": "Graph-Augmented RAG Engine",
                "status": "complete",
                "tests": "20+ passed",
            },
            "tahap_5": {
                "name": "FastAPI REST API",
                "status": "active",
            },
        },
        "endpoints": {
            "chat": "/api/v1/chat",
            "documents": "/api/v1/documents",
            "graph": "/api/v1/graph",
            "docs": "/docs",
            "redoc": "/redoc",
        }
    }


@router.get("/uptime", tags=["stats"])
async def get_uptime():
    """Get uptime."""
    uptime = (datetime.now() - startup_time).total_seconds()
    
    hours = int(uptime // 3600)
    minutes = int((uptime % 3600) // 60)
    seconds = int(uptime % 60)
    
    return {
        "uptime_seconds": uptime,
        "uptime_formatted": f"{hours}h {minutes}m {seconds}s",
        "startup_time": startup_time.isoformat(),
    }


@router.get("/components", tags=["info"])
async def get_components_status():
    """Get status of all components."""
    components = {}
    
    # Neo4j
    neo4j_status = "unavailable"
    if app_state["neo4j_client"]:
        try:
            app_state["neo4j_client"].health_check()
            neo4j_status = "healthy"
        except Exception as e:
            neo4j_status = f"error: {str(e)}"
    
    components["neo4j"] = {
        "status": neo4j_status,
        "type": "Graph Database",
        "version": "5.15.0",
    }
    
    # Vector Manager
    components["vector_manager"] = {
        "status": "healthy" if app_state["vector_manager"] else "unavailable",
        "type": "Embedding & Vector Search",
        "provider": "openai",
    }
    
    # RAG Engine
    components["rag_engine"] = {
        "status": "healthy" if app_state["rag"] else "unavailable",
        "type": "Question Answering",
        "model": "gemini-1.5-pro",
    }
    
    return components


@router.get("/version", tags=["info"])
async def get_version():
    """Get version information."""
    return {
        "api_version": "1.0.0",
        "legalkg_version": "1.0.0",
        "api_level": "v1",
        "python_version": __import__('sys').version,
        "fastapi_version": __import__('fastapi').__version__,
    }
