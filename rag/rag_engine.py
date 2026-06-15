"""
RAG Engine - Main Orchestrator

Combines retriever, context manager, and LLM reasoner for end-to-end RAG.
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import logging
from datetime import datetime
import json
from pathlib import Path

from .retriever import MultiStrategyRetriever, RetrievalStrategy, RetrievedDocument
from .context_manager import ContextManager, ContextWindow
from .llm_reasoner import LLMReasoner, ReasoningResult
from graph.neo4j_client import Neo4jClient
from graph.vector_manager import VectorManager


logger = logging.getLogger(__name__)


@dataclass
class RAGConfig:
    """RAG configuration."""
    max_context_tokens: int = 4000
    chunk_size: int = 500
    chunk_overlap: int = 50
    retrieval_strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    graph_depth: int = 2
    top_k_documents: int = 5
    confidence_threshold: float = 0.5
    include_reasoning_steps: bool = True


class RAGPipeline:
    """
    Complete RAG pipeline for legal document Q&A.
    
    Flow:
    1. Retrieval: Multi-strategy retrieval of relevant documents
    2. Context: Build and optimize context window
    3. Reasoning: LLM-based reasoning with chain-of-thought
    4. Response: Format and return answer with sources
    """
    
    def __init__(
        self,
        neo4j_client: Neo4jClient,
        vector_manager: VectorManager,
        gemini_api_key: str,
        config: RAGConfig = None,
    ):
        """
        Initialize RAG pipeline.
        
        Args:
            neo4j_client: Neo4j connection
            vector_manager: Vector embeddings manager
            gemini_api_key: Google Gemini API key
            config: RAG configuration
        """
        self.neo4j_client = neo4j_client
        self.vector_manager = vector_manager
        self.config = config or RAGConfig()
        
        # Initialize components
        self.retriever = MultiStrategyRetriever(neo4j_client, vector_manager)
        self.context_mgr = ContextManager(
            max_context_tokens=self.config.max_context_tokens,
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        self.reasoner = LLMReasoner(gemini_api_key)
        
        self.query_history: List[Dict] = []
    
    def query(
        self,
        question: str,
        retrieve_sources: bool = True,
        include_followup: bool = False,
        followup_question: str = None,
    ) -> Dict:
        """
        Process user query through complete RAG pipeline.
        
        Args:
            question: User question
            retrieve_sources: Include source documents
            include_followup: Process follow-up question
            followup_question: Optional follow-up question
            
        Returns:
            Dict with answer, sources, reasoning, stats
        """
        import time
        start_time = time.time()
        
        try:
            logger.info(f"Processing query: {question[:100]}...")
            
            # Step 1: Retrieve relevant documents
            logger.info("Step 1: Retrieving documents...")
            retrieved, retrieval_stats = self.retriever.retrieve(
                question,
                top_k=self.config.top_k_documents,
                strategy=self.config.retrieval_strategy,
                graph_depth=self.config.graph_depth,
            )
            
            if not retrieved:
                logger.warning("No relevant documents found")
                return {
                    "answer": "Maaf, tidak ada dokumen hukum yang relevan ditemukan untuk pertanyaan Anda.",
                    "sources": [],
                    "confidence": 0.0,
                    "processing_time_ms": (time.time() - start_time) * 1000,
                }
            
            # Step 2: Build context window
            logger.info("Step 2: Building context window...")
            context_window = self.context_mgr.create_context_window(retrieved, question)
            context_window = self.context_mgr.optimize_context_order(context_window, strategy="relevance")
            
            # Format context for LLM
            context_text = self.context_mgr.format_context_for_llm(context_window, include_metadata=True)
            
            # Step 3: Perform reasoning
            logger.info("Step 3: Performing LLM reasoning...")
            result = self.reasoner.reason(
                question=question,
                context=context_text,
                retrieve_reasoning_steps=self.config.include_reasoning_steps,
                confidence_threshold=self.config.confidence_threshold,
            )
            
            # Step 4: Handle follow-up if requested
            followup_result = None
            if include_followup and followup_question:
                logger.info("Step 4: Processing follow-up question...")
                followup_result, _ = self.reasoner.reason_with_followup(
                    question, context_text, followup_question
                )
            
            # Build response
            response = {
                "answer": result.answer,
                "question": question,
                "confidence": result.confidence,
                "sources": result.sources if retrieve_sources else [],
                "reasoning_steps": result.reasoning_steps,
                "processing_time_ms": (time.time() - start_time) * 1000,
                "stats": {
                    "documents_retrieved": retrieval_stats.total_documents,
                    "retrieval_time_ms": retrieval_stats.execution_time_ms,
                    "context_chunks": len(context_window.chunks),
                    "context_tokens": context_window.used_tokens,
                    "model": result.model,
                },
            }
            
            if followup_result:
                response["followup_answer"] = followup_result.answer
                response["followup_confidence"] = followup_result.confidence
            
            # Store in history
            self.query_history.append({
                "question": question,
                "answer": result.answer,
                "confidence": result.confidence,
                "timestamp": datetime.now().isoformat(),
                "processing_time_ms": response["processing_time_ms"],
            })
            
            logger.info(f"Query processed successfully: {result.confidence:.1%} confidence")
            
            return response
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}", exc_info=True)
            return {
                "answer": f"Terjadi kesalahan: {str(e)}",
                "error": str(e),
                "confidence": 0.0,
                "processing_time_ms": (time.time() - start_time) * 1000,
            }
    
    def batch_query(
        self,
        questions: List[str],
        save_results: bool = False,
        output_dir: str = "./data",
    ) -> List[Dict]:
        """
        Process batch of questions.
        
        Args:
            questions: List of questions
            save_results: Save results to JSON
            output_dir: Output directory
            
        Returns:
            List of results
        """
        results = []
        
        for i, question in enumerate(questions, 1):
            logger.info(f"Processing batch query {i}/{len(questions)}")
            result = self.query(question)
            results.append(result)
        
        # Save results if requested
        if save_results:
            output_file = Path(output_dir) / f"rag_batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Results saved to {output_file}")
        
        return results
    
    def explain_answer(
        self, answer: str, context: str, num_points: int = 5
    ) -> Dict:
        """
        Provide detailed explanation of answer.
        
        Args:
            answer: Generated answer
            context: Retrieved context
            num_points: Number of key points
            
        Returns:
            Dict with explanation, key points, summary
        """
        try:
            # Extract key points
            key_points = self.reasoner.extract_key_points(context, num_points)
            
            # Create summary
            summary = self.reasoner.create_summary(context, max_length=500)
            
            return {
                "answer": answer,
                "key_points": key_points,
                "summary": summary,
                "context_length": len(context),
            }
            
        except Exception as e:
            logger.error(f"Explanation failed: {e}")
            return {
                "answer": answer,
                "key_points": [],
                "summary": "",
                "error": str(e),
            }
    
    def save_query_history(self, output_file: str = "./data/rag_query_history.json"):
        """Save query history to file."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.query_history, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Query history saved to {output_file}")
    
    def get_statistics(self) -> Dict:
        """Get comprehensive RAG statistics."""
        return {
            "total_queries": len(self.query_history),
            "avg_confidence": sum(q["confidence"] for q in self.query_history) / len(self.query_history) if self.query_history else 0,
            "retriever_stats": self.retriever.get_stats(),
            "context_stats": self.context_mgr.get_stats(),
            "reasoner_stats": self.reasoner.get_stats(),
        }


# Convenience alias
RAGEngine = RAGPipeline
