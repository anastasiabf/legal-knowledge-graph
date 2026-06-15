"""
Chat Routes - Q&A Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List
import logging
import time

from api.models import ChatRequest, ChatResponse, BatchChatRequest, BatchChatResponse, ErrorResponse
from api.main import app_state
from rag.retriever import RetrievalStrategy


logger = logging.getLogger("legalkg.api.chat")
router = APIRouter()


def get_rag():
    """Get RAG engine."""
    if not app_state["rag"]:
        raise HTTPException(
            status_code=503,
            detail="RAG engine not available. Check GOOGLE_GEMINI_API_KEY environment variable."
        )
    return app_state["rag"]


@router.post("/query", response_model=ChatResponse, responses={503: {"model": ErrorResponse}})
async def chat_query(request: ChatRequest, rag = Depends(get_rag)):
    """
    Ask a question about legal documents.
    
    - **question**: The question to ask
    - **strategy**: Retrieval strategy (vector, graph, bm25, hybrid)
    - **top_k**: Number of documents to retrieve (1-20)
    - **include_reasoning**: Include chain-of-thought reasoning steps
    - **max_context_tokens**: Maximum context window size (1000-10000)
    """
    try:
        logger.info(f"Chat query: {request.question[:50]}...")
        
        start_time = time.time()
        
        # Convert strategy string to enum
        strategy_map = {
            "vector": RetrievalStrategy.VECTOR,
            "graph": RetrievalStrategy.GRAPH,
            "bm25": RetrievalStrategy.BM25,
            "hybrid": RetrievalStrategy.HYBRID,
        }
        
        strategy = strategy_map.get(request.strategy.value, RetrievalStrategy.HYBRID)
        
        # Update RAG config
        rag.config.top_k_documents = request.top_k
        rag.config.max_context_tokens = request.max_context_tokens
        rag.config.retrieval_strategy = strategy
        rag.config.include_reasoning_steps = request.include_reasoning
        
        # Process query
        result = rag.query(
            request.question,
            retrieve_sources=True,
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        return ChatResponse(
            answer=result["answer"],
            confidence=result.get("confidence", 0.0),
            sources=result.get("sources", []),
            reasoning_steps=result.get("reasoning_steps", []),
            processing_time_ms=processing_time,
        )
        
    except Exception as e:
        logger.error(f"Chat query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )


@router.post("/batch", response_model=BatchChatResponse, responses={503: {"model": ErrorResponse}})
async def chat_batch(request: BatchChatRequest, rag = Depends(get_rag)):
    """
    Process multiple questions in batch.
    
    - **questions**: List of questions to ask (1-100)
    - **strategy**: Retrieval strategy for all questions
    - **parallel**: Process questions in parallel (if True)
    """
    try:
        logger.info(f"Batch chat: {len(request.questions)} questions")
        
        start_time = time.time()
        
        # Convert strategy
        strategy_map = {
            "vector": RetrievalStrategy.VECTOR,
            "graph": RetrievalStrategy.GRAPH,
            "bm25": RetrievalStrategy.BM25,
            "hybrid": RetrievalStrategy.HYBRID,
        }
        
        strategy = strategy_map.get(request.strategy.value, RetrievalStrategy.HYBRID)
        rag.config.retrieval_strategy = strategy
        
        # Process questions
        results = []
        failed_count = 0
        
        for question in request.questions:
            try:
                result = rag.query(question, retrieve_sources=True)
                
                chat_result = ChatResponse(
                    answer=result["answer"],
                    confidence=result.get("confidence", 0.0),
                    sources=result.get("sources", []),
                    reasoning_steps=result.get("reasoning_steps", []),
                    processing_time_ms=result.get("processing_time_ms", 0),
                )
                results.append(chat_result)
                
            except Exception as e:
                logger.error(f"Batch question failed: {e}")
                failed_count += 1
                
                # Add error response
                results.append(ChatResponse(
                    answer=f"Error processing question: {str(e)}",
                    confidence=0.0,
                    processing_time_ms=0,
                ))
        
        total_time = (time.time() - start_time) * 1000
        
        return BatchChatResponse(
            results=results,
            total_time_ms=total_time,
            failed_count=failed_count,
        )
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing failed: {str(e)}"
        )


@router.get("/health", tags=["health"])
async def chat_health():
    """Check chat endpoint health."""
    return {
        "status": "healthy" if app_state["rag"] else "unavailable",
        "rag_available": app_state["rag"] is not None,
    }
