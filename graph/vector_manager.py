"""
Vector Manager - Manage embeddings and vector search for Neo4j

Handles vector index creation, embedding generation, and semantic search.
Integrates with OpenAI or Google Gemini for embeddings.
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from graph.neo4j_client import Neo4jClient
from ingestion.utils import get_logger


logger = get_logger("legalkg.vector_manager")


@dataclass
class VectorConfig:
    """Configuration for vector management."""
    embedding_model: str = "text-embedding-3-small"  # OpenAI
    embedding_dimensions: int = 1536
    similarity_metric: str = "cosine"
    batch_size: int = 100
    provider: str = "openai"  # 'openai' or 'google'


class VectorManager:
    """Manage embeddings and vector search in Neo4j."""
    
    def __init__(
        self,
        neo4j_client: Neo4jClient,
        config: VectorConfig = None,
        api_key: str = None,
    ):
        """
        Initialize vector manager.
        
        Args:
            neo4j_client: Connected Neo4j client
            config: Vector configuration
            api_key: API key for embedding provider
        """
        self.neo4j = neo4j_client
        self.config = config or VectorConfig()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        # Initialize embedding client based on provider
        if self.config.provider == "openai":
            self._init_openai()
        elif self.config.provider == "google":
            self._init_google()
        else:
            logger.error(f"Unknown provider: {self.config.provider}")
    
    def _init_openai(self):
        """Initialize OpenAI embedding client."""
        try:
            import openai
            openai.api_key = self.api_key
            self.embedding_client = openai
            logger.info("✅ OpenAI embedding client initialized")
        except ImportError:
            logger.error("openai package not installed. Run: pip install openai")
            self.embedding_client = None
    
    def _init_google(self):
        """Initialize Google Gemini embedding client."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.embedding_client = genai
            logger.info("✅ Google Gemini embedding client initialized")
        except ImportError:
            logger.error("google-generativeai package not installed")
            self.embedding_client = None
    
    def generate_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings or None if failed
        """
        if not self.embedding_client:
            logger.error("Embedding client not initialized")
            return None
        
        try:
            if self.config.provider == "openai":
                response = self.embedding_client.Embedding.create(
                    input=texts,
                    model=self.config.embedding_model,
                )
                embeddings = [item["embedding"] for item in response["data"]]
                return embeddings
            
            elif self.config.provider == "google":
                embeddings = []
                for text in texts:
                    result = self.embedding_client.embed_content(
                        model="models/embedding-001",
                        content=text,
                    )
                    embeddings.append(result["embedding"])
                return embeddings
        
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return None
    
    def embed_pasals(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        Generate and store embeddings for all Pasal nodes.
        
        Args:
            batch_size: Number of pasals to process at once
            
        Returns:
            Processing statistics
        """
        logger.info("🔄 Generating embeddings for Pasals...")
        
        stats = {
            "total_pasals": 0,
            "embedded": 0,
            "failed": 0,
        }
        
        # Get all pasals
        query = """
        MATCH (p:Pasal)
        RETURN p.id as id, p.judul as judul, p.full_text as full_text
        LIMIT $limit
        """
        
        offset = 0
        while True:
            pasals = self.neo4j.execute_query(query, {"limit": batch_size})
            if not pasals:
                break
            
            stats["total_pasals"] += len(pasals)
            
            # Prepare texts
            texts = [
                f"{p['judul']}\n{p['full_text']}"
                for p in pasals
            ]
            
            # Generate embeddings
            embeddings = self.generate_embeddings(texts)
            if not embeddings:
                stats["failed"] += len(pasals)
                continue
            
            # Store in Neo4j
            for pasal, embedding in zip(pasals, embeddings):
                update_query = """
                MATCH (p:Pasal {id: $id})
                SET p.embedding = $embedding,
                    p.embedding_model = $model,
                    p.embedding_updated_at = $updated_at
                """
                
                result = self.neo4j.execute_write_transaction(
                    update_query,
                    {
                        "id": pasal["id"],
                        "embedding": embedding,
                        "model": self.config.embedding_model,
                        "updated_at": datetime.now().isoformat(),
                    }
                )
                
                if result.get("success"):
                    stats["embedded"] += 1
                else:
                    stats["failed"] += 1
            
            offset += batch_size
        
        logger.info(f"✅ Embedded {stats['embedded']} pasals")
        return stats
    
    def embed_konsep_hukum(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        Generate and store embeddings for KonsepHukum nodes.
        
        Args:
            batch_size: Number of concepts to process at once
            
        Returns:
            Processing statistics
        """
        logger.info("🔄 Generating embeddings for KonsepHukum...")
        
        stats = {
            "total_konsep": 0,
            "embedded": 0,
            "failed": 0,
        }
        
        # Get all konsep hukum
        query = """
        MATCH (k:KonsepHukum)
        RETURN k.id as id, k.nama as nama, k.definisi as definisi
        LIMIT $limit
        """
        
        offset = 0
        while True:
            konseps = self.neo4j.execute_query(query, {"limit": batch_size})
            if not konseps:
                break
            
            stats["total_konsep"] += len(konseps)
            
            # Prepare texts
            texts = [
                f"{k['nama']}\n{k['definisi']}"
                for k in konseps
            ]
            
            # Generate embeddings
            embeddings = self.generate_embeddings(texts)
            if not embeddings:
                stats["failed"] += len(konseps)
                continue
            
            # Store in Neo4j
            for konsep, embedding in zip(konseps, embeddings):
                update_query = """
                MATCH (k:KonsepHukum {id: $id})
                SET k.embedding = $embedding,
                    k.embedding_model = $model,
                    k.embedding_updated_at = $updated_at
                """
                
                result = self.neo4j.execute_write_transaction(
                    update_query,
                    {
                        "id": konsep["id"],
                        "embedding": embedding,
                        "model": self.config.embedding_model,
                        "updated_at": datetime.now().isoformat(),
                    }
                )
                
                if result.get("success"):
                    stats["embedded"] += 1
                else:
                    stats["failed"] += 1
            
            offset += batch_size
        
        logger.info(f"✅ Embedded {stats['embedded']} konsep hukum")
        return stats
    
    def semantic_search_pasal(
        self,
        query_text: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for pasals.
        
        Args:
            query_text: Query text
            top_k: Number of results to return
            
        Returns:
            List of matching pasals with scores
        """
        # Generate query embedding
        query_embedding = self.generate_embeddings([query_text])
        if not query_embedding:
            return []
        
        # Search in Neo4j using vector index
        search_query = """
        CALL db.index.vector.queryNodes('idx_pasal_embedding', $top_k, $embedding)
        YIELD node as pasal, score
        RETURN pasal.id as id, pasal.nomor as nomor, 
               pasal.judul as judul, pasal.full_text as full_text,
               score
        """
        
        results = self.neo4j.execute_query(
            search_query,
            {
                "embedding": query_embedding[0],
                "top_k": top_k,
            }
        )
        
        return results
    
    def semantic_search_konsep(
        self,
        query_text: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for legal concepts.
        
        Args:
            query_text: Query text
            top_k: Number of results to return
            
        Returns:
            List of matching concepts with scores
        """
        # Generate query embedding
        query_embedding = self.generate_embeddings([query_text])
        if not query_embedding:
            return []
        
        # Search in Neo4j using vector index
        search_query = """
        CALL db.index.vector.queryNodes('idx_konsep_embedding', $top_k, $embedding)
        YIELD node as konsep, score
        RETURN konsep.id as id, konsep.nama as nama,
               konsep.definisi as definisi, konsep.frequency as frequency,
               score
        """
        
        results = self.neo4j.execute_query(
            search_query,
            {
                "embedding": query_embedding[0],
                "top_k": top_k,
            }
        )
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get vector index statistics."""
        try:
            # Get index stats
            stats_query = """
            SHOW INDEXES
            WHERE name LIKE '%embedding%'
            RETURN name, type, state, populationProgress, populationCompletionEstimate
            """
            
            results = self.neo4j.execute_query(stats_query)
            return {
                "indexes": results,
                "provider": self.config.provider,
                "model": self.config.embedding_model,
                "dimensions": self.config.embedding_dimensions,
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}


# Utility functions

def setup_vector_indexes(neo4j_client: Neo4jClient) -> bool:
    """
    Create vector indexes in Neo4j.
    
    Args:
        neo4j_client: Connected Neo4j client
        
    Returns:
        True if successful
    """
    logger.info("📊 Creating vector indexes...")
    
    try:
        # Vector index for Pasal
        pasal_index = """
        CREATE VECTOR INDEX idx_pasal_embedding IF NOT EXISTS
        FOR (p:Pasal) ON (p.embedding)
        OPTIONS {
            indexConfig: {
                `vector.dimensions`: 1536,
                `vector.similarity_metric`: 'cosine'
            }
        }
        """
        
        # Vector index for KonsepHukum
        konsep_index = """
        CREATE VECTOR INDEX idx_konsep_embedding IF NOT EXISTS
        FOR (k:KonsepHukum) ON (k.embedding)
        OPTIONS {
            indexConfig: {
                `vector.dimensions`: 1536,
                `vector.similarity_metric`: 'cosine'
            }
        }
        """
        
        neo4j_client.execute_query(pasal_index)
        neo4j_client.execute_query(konsep_index)
        
        logger.info("✅ Vector indexes created")
        return True
    
    except Exception as e:
        logger.error(f"Failed to create vector indexes: {e}")
        return False


if __name__ == "__main__":
    from datetime import datetime
