"""
TAHAP 4: RAG Engine Examples

Demonstrates complete RAG pipeline usage.
"""

import os
from typing import List

from graph.neo4j_client import create_neo4j_client
from graph.vector_manager import VectorManager, VectorConfig
from rag.rag_engine import RAGEngine, RAGConfig
from rag.retriever import RetrievalStrategy
from ingestion.utils import get_logger


logger = get_logger("rag.examples")


def example_1_basic_query():
    """Example 1: Basic query through RAG pipeline."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 1: Basic RAG Query")
    logger.info("="*80)
    
    # Initialize components
    neo4j_client = create_neo4j_client()
    if not neo4j_client:
        logger.error("Neo4j connection failed")
        return
    
    try:
        # Create vector manager
        vector_config = VectorConfig(provider="openai")
        vector_manager = VectorManager(neo4j_client, vector_config)
        
        # Create RAG engine
        rag_config = RAGConfig(
            max_context_tokens=3000,
            top_k_documents=5,
            retrieval_strategy=RetrievalStrategy.HYBRID,
        )
        
        rag = RAGEngine(
            neo4j_client=neo4j_client,
            vector_manager=vector_manager,
            gemini_api_key=os.getenv("GOOGLE_GEMINI_API_KEY"),
            config=rag_config,
        )
        
        # Query
        question = "Apa saja kewajiban penerima barang dalam transaksi elektronik?"
        logger.info(f"\nQuestion: {question}\n")
        
        result = rag.query(question, retrieve_sources=True)
        
        logger.info(f"\nAnswer:\n{result['answer']}\n")
        logger.info(f"Confidence: {result['confidence']:.1%}")
        logger.info(f"Processing time: {result['processing_time_ms']:.1f}ms")
        logger.info(f"Documents retrieved: {result['stats']['documents_retrieved']}")
        logger.info(f"Sources: {result['sources']}")
        
    finally:
        neo4j_client.disconnect()


def example_2_multiple_strategies():
    """Example 2: Compare different retrieval strategies."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 2: Comparing Retrieval Strategies")
    logger.info("="*80)
    
    neo4j_client = create_neo4j_client()
    if not neo4j_client:
        logger.error("Neo4j connection failed")
        return
    
    try:
        vector_config = VectorConfig(provider="openai")
        vector_manager = VectorManager(neo4j_client, vector_config)
        
        rag = RAGEngine(
            neo4j_client=neo4j_client,
            vector_manager=vector_manager,
            gemini_api_key=os.getenv("GOOGLE_GEMINI_API_KEY"),
        )
        
        question = "Bagaimana prosedur pembatalan transaksi elektronik?"
        
        strategies = [
            RetrievalStrategy.VECTOR,
            RetrievalStrategy.GRAPH,
            RetrievalStrategy.BM25,
            RetrievalStrategy.HYBRID,
        ]
        
        logger.info(f"\nQuestion: {question}\n")
        
        for strategy in strategies:
            logger.info(f"\nStrategy: {strategy.value}")
            logger.info("-" * 40)
            
            rag.config.retrieval_strategy = strategy
            result = rag.query(question)
            
            logger.info(f"Confidence: {result['confidence']:.1%}")
            logger.info(f"Documents: {result['stats']['documents_retrieved']}")
            logger.info(f"Time: {result['stats']['retrieval_time_ms']:.1f}ms")
    
    finally:
        neo4j_client.disconnect()


def example_3_batch_queries():
    """Example 3: Process batch of questions."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 3: Batch Query Processing")
    logger.info("="*80)
    
    neo4j_client = create_neo4j_client()
    if not neo4j_client:
        logger.error("Neo4j connection failed")
        return
    
    try:
        vector_config = VectorConfig(provider="openai")
        vector_manager = VectorManager(neo4j_client, vector_config)
        
        rag = RAGEngine(
            neo4j_client=neo4j_client,
            vector_manager=vector_manager,
            gemini_api_key=os.getenv("GOOGLE_GEMINI_API_KEY"),
        )
        
        questions = [
            "Apa definisi transaksi elektronik?",
            "Siapa yang bertanggung jawab atas keamanan data?",
            "Bagaimana cara menyelesaikan sengketa elektronik?",
        ]
        
        logger.info(f"\nProcessing {len(questions)} questions...\n")
        
        results = rag.batch_query(questions, save_results=True)
        
        logger.info(f"\n\nBatch Results:")
        for i, result in enumerate(results, 1):
            logger.info(f"{i}. Q: {result['question'][:50]}...")
            logger.info(f"   Confidence: {result['confidence']:.1%}")
            logger.info(f"   Time: {result['processing_time_ms']:.1f}ms\n")
        
        # Save history
        rag.save_query_history()
        
    finally:
        neo4j_client.disconnect()


def example_4_context_optimization():
    """Example 4: Context window optimization."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 4: Context Window Optimization")
    logger.info("="*80)
    
    neo4j_client = create_neo4j_client()
    if not neo4j_client:
        logger.error("Neo4j connection failed")
        return
    
    try:
        vector_config = VectorConfig(provider="openai")
        vector_manager = VectorManager(neo4j_client, vector_config)
        
        rag = RAGEngine(
            neo4j_client=neo4j_client,
            vector_manager=vector_manager,
            gemini_api_key=os.getenv("GOOGLE_GEMINI_API_KEY"),
        )
        
        question = "Jelaskan mekanisme penyelesaian sengketa elektronik"
        
        # Test different context sizes
        context_sizes = [2000, 3000, 4000]
        
        logger.info(f"\nQuestion: {question}\n")
        
        for max_tokens in context_sizes:
            logger.info(f"\nContext limit: {max_tokens} tokens")
            logger.info("-" * 40)
            
            rag.config.max_context_tokens = max_tokens
            result = rag.query(question)
            
            logger.info(f"Context tokens used: {result['stats']['context_tokens']}")
            logger.info(f"Context chunks: {result['stats']['context_chunks']}")
            logger.info(f"Confidence: {result['confidence']:.1%}")
            logger.info(f"Answer length: {len(result['answer'])} chars")
    
    finally:
        neo4j_client.disconnect()


def example_5_detailed_explanation():
    """Example 5: Get detailed explanation of answer."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 5: Detailed Answer Explanation")
    logger.info("="*80)
    
    neo4j_client = create_neo4j_client()
    if not neo4j_client:
        logger.error("Neo4j connection failed")
        return
    
    try:
        vector_config = VectorConfig(provider="openai")
        vector_manager = VectorManager(neo4j_client, vector_config)
        
        rag = RAGEngine(
            neo4j_client=neo4j_client,
            vector_manager=vector_manager,
            gemini_api_key=os.getenv("GOOGLE_GEMINI_API_KEY"),
        )
        
        question = "Apa saja hak konsumen dalam transaksi elektronik?"
        
        logger.info(f"\nQuestion: {question}\n")
        
        result = rag.query(question, retrieve_sources=True)
        
        logger.info(f"Answer:\n{result['answer']}\n")
        
        # Get explanation
        explanation = rag.explain_answer(
            result['answer'],
            "",  # Would use actual context from result
            num_points=5
        )
        
        logger.info("Key Points:")
        for i, point in enumerate(explanation['key_points'], 1):
            logger.info(f"{i}. {point}")
        
        logger.info(f"\nSummary:\n{explanation['summary']}")
    
    finally:
        neo4j_client.disconnect()


def example_6_statistics():
    """Example 6: View RAG statistics."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 6: RAG Statistics")
    logger.info("="*80)
    
    neo4j_client = create_neo4j_client()
    if not neo4j_client:
        logger.error("Neo4j connection failed")
        return
    
    try:
        vector_config = VectorConfig(provider="openai")
        vector_manager = VectorManager(neo4j_client, vector_config)
        
        rag = RAGEngine(
            neo4j_client=neo4j_client,
            vector_manager=vector_manager,
            gemini_api_key=os.getenv("GOOGLE_GEMINI_API_KEY"),
        )
        
        # Process a few queries
        questions = [
            "Apa itu transaksi elektronik?",
            "Bagaimana perlindungan data pribadi?",
        ]
        
        for q in questions:
            logger.info(f"Processing: {q}")
            rag.query(q)
        
        # Get statistics
        stats = rag.get_statistics()
        
        logger.info("\n\nStatistics:")
        logger.info(f"Total queries: {stats['total_queries']}")
        logger.info(f"Average confidence: {stats['avg_confidence']:.1%}")
        
        logger.info("\nRetriever stats:")
        if stats['retriever_stats']:
            logger.info(f"  Total retrievals: {stats['retriever_stats'].get('total_retrievals', 0)}")
            logger.info(f"  Avg time: {stats['retriever_stats'].get('avg_execution_time_ms', 0):.1f}ms")
        
        logger.info("\nContext stats:")
        if stats['context_stats']:
            logger.info(f"  Total windows: {stats['context_stats'].get('total_windows', 0)}")
            logger.info(f"  Avg tokens: {stats['context_stats'].get('avg_tokens_per_window', 0):.0f}")
        
        logger.info("\nReasoner stats:")
        if stats['reasoner_stats']:
            logger.info(f"  Total reasonings: {stats['reasoner_stats'].get('total_reasonings', 0)}")
            logger.info(f"  Avg confidence: {stats['reasoner_stats'].get('avg_confidence', 0):.1%}")
            logger.info(f"  Total tokens: {stats['reasoner_stats'].get('total_tokens', 0)}")
    
    finally:
        neo4j_client.disconnect()


def main():
    """Run all examples."""
    logger.info("\n" + "="*80)
    logger.info("TAHAP 4: RAG ENGINE EXAMPLES")
    logger.info("="*80)
    
    # Check API key
    if not os.getenv("GOOGLE_GEMINI_API_KEY"):
        logger.error("GOOGLE_GEMINI_API_KEY not set")
        return
    
    examples = [
        ("Example 1: Basic Query", example_1_basic_query),
        ("Example 2: Comparison", example_2_multiple_strategies),
        ("Example 3: Batch Queries", example_3_batch_queries),
        ("Example 4: Context Optimization", example_4_context_optimization),
        ("Example 5: Detailed Explanation", example_5_detailed_explanation),
        ("Example 6: Statistics", example_6_statistics),
    ]
    
    for name, example_func in examples:
        try:
            logger.info(f"\nRunning {name}...")
            example_func()
        except Exception as e:
            logger.error(f"Example failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()
