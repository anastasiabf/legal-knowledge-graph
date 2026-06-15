"""
Tests for TAHAP 4: RAG Engine
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from rag.retriever import (
    RetrievedDocument,
    RetrievalStats,
    MultiStrategyRetriever,
    RetrievalStrategy,
)
from rag.context_manager import (
    ContextChunk,
    ContextWindow,
    ContextManager,
)
from rag.llm_reasoner import ReasoningResult, LLMReasoner
from rag.rag_engine import RAGConfig, RAGEngine


class TestRetrievedDocument:
    """Test RetrievedDocument model."""
    
    def test_creation(self):
        """Test document creation."""
        doc = RetrievedDocument(
            nomor_pasal="1",
            nomor_peraturan="UU No. 11 Tahun 2008",
            judul_pasal="Definisi",
            judul_peraturan="ITE Law",
            pasal_text="Transaksi elektronik adalah...",
            score=0.9,
            strategy=RetrievalStrategy.VECTOR,
        )
        
        assert doc.nomor_pasal == "1"
        assert doc.score == 0.9
        assert doc.strategy == RetrievalStrategy.VECTOR
    
    def test_to_dict(self):
        """Test conversion to dict."""
        doc = RetrievedDocument(
            nomor_pasal="1",
            nomor_peraturan="UU 11/2008",
            judul_pasal="Definisi",
            judul_peraturan="ITE",
            pasal_text="Text",
            score=0.85,
            strategy=RetrievalStrategy.HYBRID,
        )
        
        result = doc.to_dict()
        assert result["nomor_pasal"] == "1"
        assert result["strategy"] == "hybrid"


class TestContextChunk:
    """Test ContextChunk model."""
    
    def test_creation(self):
        """Test chunk creation."""
        chunk = ContextChunk(
            content="This is a chunk",
            chunk_id=1,
            source_pasal="1",
            source_peraturan="UU 11/2008",
            start_position=0,
            end_position=14,
        )
        
        assert chunk.chunk_id == 1
        assert len(chunk.content) > 0
    
    def test_token_count(self):
        """Test token count estimation."""
        chunk = ContextChunk(
            content="A" * 400,  # 400 chars ≈ 100 tokens
            chunk_id=1,
            source_pasal="1",
            source_peraturan="UU",
            start_position=0,
            end_position=400,
        )
        
        tokens = chunk.token_count()
        assert tokens == 100


class TestContextManager:
    """Test ContextManager."""
    
    def test_initialization(self):
        """Test context manager initialization."""
        mgr = ContextManager(max_context_tokens=4000)
        assert mgr.max_context_tokens == 4000
    
    def test_chunk_document(self):
        """Test document chunking."""
        mgr = ContextManager(chunk_size=100, chunk_overlap=10)
        
        text = "A" * 250  # Long text
        chunks = mgr._chunk_document(text, "1", "UU 11/2008", 0.9, 0)
        
        assert len(chunks) > 1
        assert all(len(c.content) <= 100 for c in chunks)
    
    def test_create_context_window(self):
        """Test context window creation."""
        mgr = ContextManager(max_context_tokens=2000)
        
        # Mock retrieved documents
        docs = [
            Mock(
                pasal_text="Pasal 1: Definisi",
                nomor_pasal="1",
                nomor_peraturan="UU 11/2008",
                score=0.9,
            )
        ]
        
        window = mgr.create_context_window(docs)
        
        assert window.window_id is not None
        assert len(window.chunks) > 0
        assert window.used_tokens > 0


class TestContextWindow:
    """Test ContextWindow model."""
    
    def test_get_content(self):
        """Test getting concatenated content."""
        chunks = [
            ContextChunk("Content 1", 1, "1", "UU 11", 0, 9),
            ContextChunk("Content 2", 2, "2", "UU 11", 10, 19),
        ]
        
        window = ContextWindow(chunks, "w1", 4000)
        content = window.get_content()
        
        assert "Content 1" in content
        assert "Content 2" in content


class TestReasoningResult:
    """Test ReasoningResult model."""
    
    def test_creation(self):
        """Test result creation."""
        result = ReasoningResult(
            answer="Answer text",
            confidence=0.85,
            tokens_used=500,
        )
        
        assert result.answer == "Answer text"
        assert result.confidence == 0.85
    
    def test_to_dict(self):
        """Test conversion to dict."""
        result = ReasoningResult(
            answer="Answer",
            confidence=0.9,
            tokens_used=100,
        )
        
        d = result.to_dict()
        assert d["answer"] == "Answer"
        assert d["confidence"] == 0.9


class TestMultiStrategyRetriever:
    """Test MultiStrategyRetriever."""
    
    def test_initialization(self):
        """Test retriever initialization."""
        neo4j_client = Mock()
        retriever = MultiStrategyRetriever(neo4j_client)
        
        assert retriever.neo4j_client is not None
    
    def test_deduplicate_results(self):
        """Test deduplication."""
        retriever = MultiStrategyRetriever(Mock())
        
        docs = [
            RetrievedDocument("1", "UU 11", "Def", "ITE", "Text", 0.9, RetrievalStrategy.VECTOR),
            RetrievedDocument("1", "UU 11", "Def", "ITE", "Text", 0.8, RetrievalStrategy.BM25),
            RetrievedDocument("2", "UU 11", "Art", "ITE", "Text", 0.7, RetrievalStrategy.GRAPH),
        ]
        
        deduplicated = retriever._deduplicate_results(docs)
        
        assert len(deduplicated) == 2
        # Should keep highest score for pasal 1
        assert deduplicated[0].score >= deduplicated[1].score


class TestRAGConfig:
    """Test RAGConfig."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = RAGConfig()
        
        assert config.max_context_tokens == 4000
        assert config.top_k_documents == 5
        assert config.retrieval_strategy == RetrievalStrategy.HYBRID


class TestRAGEngine:
    """Test RAGEngine."""
    
    @patch('rag.rag_engine.MultiStrategyRetriever')
    @patch('rag.rag_engine.ContextManager')
    @patch('rag.rag_engine.LLMReasoner')
    def test_initialization(self, mock_reasoner, mock_context, mock_retriever):
        """Test RAG engine initialization."""
        neo4j_client = Mock()
        vector_manager = Mock()
        
        rag = RAGEngine(neo4j_client, vector_manager, "fake_key")
        
        assert rag.neo4j_client is not None
        assert rag.query_history is not None


class TestRetrievalStatistics:
    """Test retrieval statistics."""
    
    def test_stats_creation(self):
        """Test stats object creation."""
        stats = RetrievalStats(
            total_documents=5,
            vector_results=3,
            graph_results=2,
            bm25_results=1,
            execution_time_ms=150.5,
            deduplication_removed=1,
        )
        
        assert stats.total_documents == 5
        assert stats.execution_time_ms == 150.5


class TestContextWindowOrdering:
    """Test context window ordering strategies."""
    
    def test_relevance_ordering(self):
        """Test relevance-based ordering."""
        mgr = ContextManager()
        
        chunks = [
            ContextChunk("Low rel", 1, "1", "UU", 0, 7, relevance_score=0.5),
            ContextChunk("High rel", 2, "2", "UU", 8, 16, relevance_score=0.9),
        ]
        
        window = ContextWindow(chunks, "w1", 4000)
        ordered = mgr.optimize_context_order(window, strategy="relevance")
        
        # Higher relevance should be first
        assert ordered.chunks[0].relevance_score >= ordered.chunks[1].relevance_score


class TestKeywordExtraction:
    """Test keyword extraction."""
    
    def test_extract_keywords(self):
        """Test keyword extraction from query."""
        retriever = MultiStrategyRetriever(Mock())
        
        query = "Apa saja kewajiban penerima barang dalam transaksi elektronik?"
        keywords = retriever._extract_keywords(query)
        
        assert len(keywords) > 0
        assert any(k in ["kewajiban", "penerima", "barang", "transaksi", "elektronik"] for k in keywords)


class TestQueryMatching:
    """Test query text matching."""
    
    def test_calculate_query_match(self):
        """Test query match calculation."""
        retriever = MultiStrategyRetriever(Mock())
        
        query = "transaksi elektronik"
        text = "Transaksi elektronik adalah proses jual beli yang dilakukan melalui sistem elektronik"
        
        score = retriever._calculate_query_match(text, query)
        
        assert score > 0
        assert score <= 1


def test_integration_context_management():
    """Integration test: Context management."""
    mgr = ContextManager(max_context_tokens=1000, chunk_size=200)
    
    # Create mock documents
    docs = [
        Mock(
            pasal_text="A" * 500,
            nomor_pasal="1",
            nomor_peraturan="UU 11/2008",
            score=0.9,
        )
    ]
    
    # Create context window
    window = mgr.create_context_window(docs)
    
    # Verify window
    assert window is not None
    assert window.used_tokens <= mgr.max_context_tokens
    assert len(window.chunks) > 0


def test_reasoning_result_consistency():
    """Test reasoning result consistency."""
    result1 = ReasoningResult(
        answer="Same answer",
        confidence=0.85,
        tokens_used=100,
    )
    
    result2 = ReasoningResult(
        answer="Same answer",
        confidence=0.85,
        tokens_used=100,
    )
    
    d1 = result1.to_dict()
    d2 = result2.to_dict()
    
    # Should have same answer and confidence
    assert d1["answer"] == d2["answer"]
    assert d1["confidence"] == d2["confidence"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
