"""
Multi-Strategy Retriever for RAG

Combines:
1. Vector Search (semantic similarity)
2. Graph Traversal (concept relationships)
3. BM25 Full-Text Search (keyword matching)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional
import logging
from datetime import datetime
import re

from graph.neo4j_client import Neo4jClient
from graph.vector_manager import VectorManager


logger = logging.getLogger(__name__)


class RetrievalStrategy(Enum):
    """Retrieval strategy types."""
    VECTOR = "vector"  # Semantic vector search
    GRAPH = "graph"    # Graph traversal
    BM25 = "bm25"      # Full-text search
    HYBRID = "hybrid"  # Combine all three


@dataclass
class RetrievedDocument:
    """Retrieved document with metadata."""
    nomor_pasal: str
    nomor_peraturan: str
    judul_pasal: str
    judul_peraturan: str
    pasal_text: str
    score: float  # 0-1 relevance score
    strategy: RetrievalStrategy  # Which strategy found it
    confidence: float = 0.0  # Confidence from extraction
    ranking: int = 0  # Position in ranking
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "nomor_pasal": self.nomor_pasal,
            "nomor_peraturan": self.nomor_peraturan,
            "judul_pasal": self.judul_pasal,
            "judul_peraturan": self.judul_peraturan,
            "pasal_text": self.pasal_text,
            "score": self.score,
            "strategy": self.strategy.value,
            "confidence": self.confidence,
            "ranking": self.ranking,
            "metadata": self.metadata,
        }


@dataclass
class RetrievalStats:
    """Statistics from retrieval."""
    total_documents: int
    vector_results: int
    graph_results: int
    bm25_results: int
    execution_time_ms: float
    deduplication_removed: int
    timestamp: datetime = field(default_factory=datetime.now)


class MultiStrategyRetriever:
    """
    Multi-strategy retriever for legal documents.
    
    Combines:
    - Vector semantic search
    - Graph traversal for relationships
    - Full-text BM25 search
    """
    
    def __init__(
        self,
        neo4j_client: Neo4jClient,
        vector_manager: VectorManager = None,
        embedding_model: str = "openai",
    ):
        """
        Initialize retriever.
        
        Args:
            neo4j_client: Neo4j connection
            vector_manager: Vector manager (if None, created internally)
            embedding_model: Embedding model ("openai" or "google")
        """
        self.neo4j_client = neo4j_client
        self.vector_manager = vector_manager
        self.embedding_model = embedding_model
        self.stats_history: List[RetrievalStats] = []
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        graph_depth: int = 2,
        use_related_concepts: bool = True,
    ) -> Tuple[List[RetrievedDocument], RetrievalStats]:
        """
        Retrieve documents using specified strategy.
        
        Args:
            query: User query text
            top_k: Number of results to return
            strategy: Retrieval strategy to use
            graph_depth: Depth for graph traversal
            use_related_concepts: Include related legal concepts
            
        Returns:
            Tuple of (retrieved_documents, stats)
        """
        import time
        start_time = time.time()
        
        results = []
        
        try:
            if strategy == RetrievalStrategy.VECTOR:
                results = self._retrieve_vector(query, top_k)
                
            elif strategy == RetrievalStrategy.GRAPH:
                results = self._retrieve_graph(query, top_k, graph_depth, use_related_concepts)
                
            elif strategy == RetrievalStrategy.BM25:
                results = self._retrieve_bm25(query, top_k)
                
            elif strategy == RetrievalStrategy.HYBRID:
                results = self._retrieve_hybrid(
                    query, top_k, graph_depth, use_related_concepts
                )
            
            # Deduplicate by nomor_pasal
            deduplicated = self._deduplicate_results(results)
            
            # Rank results
            ranked = self._rank_results(deduplicated, query)
            
            # Keep top_k
            final_results = ranked[:top_k]
            
            execution_time = (time.time() - start_time) * 1000
            
            stats = RetrievalStats(
                total_documents=len(final_results),
                vector_results=len([r for r in results if r.strategy == RetrievalStrategy.VECTOR]),
                graph_results=len([r for r in results if r.strategy == RetrievalStrategy.GRAPH]),
                bm25_results=len([r for r in results if r.strategy == RetrievalStrategy.BM25]),
                execution_time_ms=execution_time,
                deduplication_removed=len(results) - len(deduplicated),
            )
            
            self.stats_history.append(stats)
            
            logger.info(f"Retrieval completed: {stats.total_documents} results in {execution_time:.1f}ms")
            
            return final_results, stats
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}", exc_info=True)
            return [], RetrievalStats(
                total_documents=0,
                vector_results=0,
                graph_results=0,
                bm25_results=0,
                execution_time_ms=(time.time() - start_time) * 1000,
                deduplication_removed=0,
            )
    
    def _retrieve_vector(self, query: str, top_k: int) -> List[RetrievedDocument]:
        """Vector semantic search."""
        if not self.vector_manager:
            logger.warning("Vector manager not available")
            return []
        
        try:
            results = self.vector_manager.semantic_search_pasal(query, top_k=top_k)
            
            documents = []
            for i, result in enumerate(results, 1):
                doc = RetrievedDocument(
                    nomor_pasal=result.get("nomor", ""),
                    nomor_peraturan=result.get("peraturan_nomor", ""),
                    judul_pasal=result.get("judul", ""),
                    judul_peraturan=result.get("peraturan_judul", ""),
                    pasal_text=result.get("full_text", ""),
                    score=result.get("score", 0.0),
                    strategy=RetrievalStrategy.VECTOR,
                    confidence=result.get("confidence", 0.0),
                    ranking=i,
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def _retrieve_graph(
        self, query: str, top_k: int, depth: int = 2, use_concepts: bool = True
    ) -> List[RetrievedDocument]:
        """Graph traversal retrieval."""
        try:
            # Extract keywords from query
            keywords = self._extract_keywords(query)
            
            # Find related concepts
            cypher = """
            MATCH (k:KonsepHukum)
            WHERE tolower(k.nama) CONTAINS $keyword1
               OR tolower(k.nama) CONTAINS $keyword2
               OR tolower(k.definisi) CONTAINS $keyword1
            RETURN k.nama as nama, k.pasal_utama as pasal_utama
            LIMIT 10
            """
            
            concepts = self.neo4j_client.execute_query(cypher, keyword1=keywords[0] if keywords else "", keyword2=keywords[1] if len(keywords) > 1 else "")
            
            # Find pasals related to concepts
            documents = []
            seen_pasals = set()
            
            for concept in concepts:
                pasal_nomor = concept.get("pasal_utama", "")
                
                if pasal_nomor in seen_pasals:
                    continue
                seen_pasals.add(pasal_nomor)
                
                # Get pasal details
                pasal_cypher = """
                MATCH (p:Pasal {nomor: $nomor})
                OPTIONAL MATCH (p)-[:BAGIAN_DARI]->(per:Peraturan)
                RETURN p.nomor as nomor, p.judul as judul, p.full_text as text,
                       per.nomor as peraturan_nomor, per.judul as peraturan_judul
                """
                
                pasal_results = self.neo4j_client.execute_query(pasal_cypher, nomor=pasal_nomor)
                
                if pasal_results:
                    p = pasal_results[0]
                    doc = RetrievedDocument(
                        nomor_pasal=p.get("nomor", ""),
                        nomor_peraturan=p.get("peraturan_nomor", ""),
                        judul_pasal=p.get("judul", ""),
                        judul_peraturan=p.get("peraturan_judul", ""),
                        pasal_text=p.get("text", ""),
                        score=0.8,  # Graph traversal confidence
                        strategy=RetrievalStrategy.GRAPH,
                        confidence=0.85,
                        metadata={"concept": concept.get("nama", "")},
                    )
                    documents.append(doc)
                
                if len(documents) >= top_k:
                    break
            
            return documents[:top_k]
            
        except Exception as e:
            logger.error(f"Graph retrieval failed: {e}")
            return []
    
    def _retrieve_bm25(self, query: str, top_k: int) -> List[RetrievedDocument]:
        """Full-text BM25 search."""
        try:
            # Use Neo4j full-text search
            cypher = """
            CALL db.index.fulltext.queryNodes("pasal_fulltext", $query)
            YIELD node, score
            MATCH (node)-[:BAGIAN_DARI]->(per:Peraturan)
            RETURN node.nomor as nomor, node.judul as judul, node.full_text as text,
                   per.nomor as peraturan_nomor, per.judul as peraturan_judul,
                   score
            LIMIT $limit
            """
            
            results = self.neo4j_client.execute_query(
                cypher, query=query, limit=top_k
            )
            
            documents = []
            for i, r in enumerate(results, 1):
                doc = RetrievedDocument(
                    nomor_pasal=r.get("nomor", ""),
                    nomor_peraturan=r.get("peraturan_nomor", ""),
                    judul_pasal=r.get("judul", ""),
                    judul_peraturan=r.get("peraturan_judul", ""),
                    pasal_text=r.get("text", ""),
                    score=min(r.get("score", 0.0) / 100, 1.0),  # Normalize to 0-1
                    strategy=RetrievalStrategy.BM25,
                    ranking=i,
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []
    
    def _retrieve_hybrid(
        self, query: str, top_k: int, graph_depth: int = 2, use_concepts: bool = True
    ) -> List[RetrievedDocument]:
        """Hybrid retrieval combining all strategies."""
        results = []
        
        # Get results from each strategy
        vector_results = self._retrieve_vector(query, top_k * 2)
        graph_results = self._retrieve_graph(query, top_k * 2, graph_depth, use_concepts)
        bm25_results = self._retrieve_bm25(query, top_k * 2)
        
        # Combine results
        results.extend(vector_results)
        results.extend(graph_results)
        results.extend(bm25_results)
        
        return results
    
    def _deduplicate_results(self, results: List[RetrievedDocument]) -> List[RetrievedDocument]:
        """Remove duplicate pasals, keeping highest score."""
        seen = {}
        
        for doc in results:
            key = (doc.nomor_pasal, doc.nomor_peraturan)
            
            if key not in seen:
                seen[key] = doc
            else:
                # Keep document with higher score
                if doc.score > seen[key].score:
                    seen[key] = doc
        
        return list(seen.values())
    
    def _rank_results(
        self, results: List[RetrievedDocument], query: str
    ) -> List[RetrievedDocument]:
        """Rank results by multiple factors."""
        # Score factors:
        # - Primary score (40%)
        # - Confidence (30%)
        # - Strategy preference (20%)
        # - Query match (10%)
        
        for doc in results:
            strategy_boost = {
                RetrievalStrategy.VECTOR: 1.2,
                RetrievalStrategy.HYBRID: 1.1,
                RetrievalStrategy.GRAPH: 1.0,
                RetrievalStrategy.BM25: 0.9,
            }
            
            query_match = self._calculate_query_match(doc.pasal_text, query)
            
            doc.score = (
                doc.score * 0.4
                + doc.confidence * 0.3
                + strategy_boost.get(doc.strategy, 1.0) * 0.2
                + query_match * 0.1
            )
        
        # Sort by score (descending)
        return sorted(results, key=lambda x: x.score, reverse=True)
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query."""
        # Simple keyword extraction (can be improved with NLP)
        stop_words = {"dan", "atau", "di", "ke", "dari", "yang", "dalam", "untuk", "adalah"}
        
        words = query.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords[:3]  # Top 3 keywords
    
    def _calculate_query_match(self, text: str, query: str) -> float:
        """Calculate how well text matches query (0-1)."""
        query_lower = query.lower()
        text_lower = text.lower()
        
        # Count exact phrase matches
        if query_lower in text_lower:
            return 1.0
        
        # Count keyword matches
        keywords = query_lower.split()
        matches = sum(1 for kw in keywords if kw in text_lower)
        
        return min(matches / max(len(keywords), 1) * 0.8, 0.8)
    
    def get_stats(self) -> Dict:
        """Get retrieval statistics."""
        if not self.stats_history:
            return {}
        
        return {
            "total_retrievals": len(self.stats_history),
            "avg_execution_time_ms": sum(s.execution_time_ms for s in self.stats_history) / len(self.stats_history),
            "total_deduplication": sum(s.deduplication_removed for s in self.stats_history),
            "last_retrieval": self.stats_history[-1].to_dict() if self.stats_history else {},
        }
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "embedding_model": self.embedding_model,
            "stats": self.get_stats(),
        }
