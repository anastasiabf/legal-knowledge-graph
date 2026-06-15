"""
TAHAP 5: FastAPI REST API

Main FastAPI application with complete REST API for LegalKG.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZIPMiddleware
from contextlib import asynccontextmanager
import logging
import os

from api.routes import chat, documents, graph, utils
from api.middleware import RateLimitMiddleware, LoggingMiddleware


logger = logging.getLogger("legalkg.api")


# Application state
app_state = {
    "rag": None,
    "neo4j_client": None,
    "vector_manager": None,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    logger.info("Initializing LegalKG API...")
    
    try:
        from graph.neo4j_client import create_neo4j_client
        from graph.vector_manager import VectorManager, VectorConfig
        from rag.rag_engine import RAGEngine
        
        # Initialize Neo4j
        neo4j_client = create_neo4j_client()
        if not neo4j_client:
            logger.error("Failed to connect to Neo4j")
            raise RuntimeError("Neo4j connection failed")
        
        # Initialize vector manager
        vector_config = VectorConfig(provider="openai")
        vector_manager = VectorManager(neo4j_client, vector_config)
        
        # Initialize RAG engine
        gemini_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        if not gemini_key:
            logger.warning("GOOGLE_GEMINI_API_KEY not set, RAG features will be limited")
        
        rag = RAGEngine(
            neo4j_client=neo4j_client,
            vector_manager=vector_manager,
            gemini_api_key=gemini_key or "placeholder",
        ) if gemini_key else None
        
        # Store in app state
        app_state["neo4j_client"] = neo4j_client
        app_state["vector_manager"] = vector_manager
        app_state["rag"] = rag
        
        logger.info("LegalKG API initialized successfully")
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down LegalKG API...")
    
    if app_state["neo4j_client"]:
        app_state["neo4j_client"].disconnect()
    
    logger.info("LegalKG API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="LegalKG - Legal Knowledge Graph API",
    description="Graph-Augmented RAG Engine for Indonesian Legal Documents",
    version="1.0.0",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(GZIPMiddleware, minimum_size=1000)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(graph.router, prefix="/api/v1/graph", tags=["graph"])
app.include_router(utils.router, prefix="/api/v1", tags=["utils"])


@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "name": "LegalKG - Legal Knowledge Graph API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/api/v1/chat",
            "documents": "/api/v1/documents",
            "graph": "/api/v1/graph",
            "health": "/health",
            "docs": "/docs",
        }
    }


@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint."""
    status = {
        "status": "healthy",
        "components": {
            "neo4j": "unknown",
            "rag": "unknown",
        }
    }
    
    # Check Neo4j
    if app_state["neo4j_client"]:
        try:
            app_state["neo4j_client"].health_check()
            status["components"]["neo4j"] = "healthy"
        except Exception as e:
            status["components"]["neo4j"] = f"unhealthy: {str(e)}"
            status["status"] = "degraded"
    
    # Check RAG
    if app_state["rag"]:
        status["components"]["rag"] = "healthy"
    else:
        status["components"]["rag"] = "unavailable"
    
    return status


@app.get("/version", tags=["info"])
async def version():
    """Get API version."""
    return {
        "version": "1.0.0",
        "legalkg_version": "1.0.0",
        "api_level": "v1",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
