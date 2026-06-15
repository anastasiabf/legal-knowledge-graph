"""
Unit tests for graph module (TAHAP 3).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from graph.neo4j_client import Neo4jClient, Neo4jConfig
from graph.graph_loader import GraphLoader, LoaderConfig
from graph.vector_manager import VectorManager, VectorConfig


class TestNeo4jClient:
    """Test Neo4j client."""
    
    def test_neo4j_config(self):
        """Test Neo4jConfig."""
        config = Neo4jConfig(
            uri="neo4j://localhost:7687",
            username="neo4j",
            password="password",
        )
        
        assert config.uri == "neo4j://localhost:7687"
        assert config.username == "neo4j"
    
    def test_neo4j_client_initialization(self):
        """Test Neo4j client initialization."""
        client = Neo4jClient(
            uri="neo4j://localhost:7687",
            username="neo4j",
            password="password",
        )
        
        assert client is not None
        assert client.config.uri == "neo4j://localhost:7687"
        assert client._connected == False


class TestGraphLoader:
    """Test graph loader."""
    
    def test_loader_config(self):
        """Test LoaderConfig."""
        config = LoaderConfig(batch_size=1000)
        
        assert config.batch_size == 1000
        assert config.skip_existing == False
    
    def test_graph_loader_initialization(self):
        """Test graph loader initialization."""
        mock_client = Mock()
        loader = GraphLoader(mock_client)
        
        assert loader is not None
        assert loader.neo4j == mock_client
        assert loader.stats["peraturan_created"] == 0
    
    def test_loader_statistics(self):
        """Test loader statistics."""
        mock_client = Mock()
        loader = GraphLoader(mock_client)
        
        stats = loader.get_statistics()
        assert "peraturan_created" in stats
        assert "pasal_created" in stats
        assert "konsep_created" in stats


class TestVectorManager:
    """Test vector manager."""
    
    def test_vector_config(self):
        """Test VectorConfig."""
        config = VectorConfig(
            embedding_model="text-embedding-3-small",
            embedding_dimensions=1536,
        )
        
        assert config.embedding_model == "text-embedding-3-small"
        assert config.embedding_dimensions == 1536
    
    def test_vector_manager_initialization(self):
        """Test vector manager initialization."""
        mock_client = Mock()
        config = VectorConfig()
        
        vector_mgr = VectorManager(mock_client, config, api_key="test_key")
        
        assert vector_mgr is not None
        assert vector_mgr.neo4j == mock_client
        assert vector_mgr.config == config


class TestGraphSchema:
    """Test graph schema structure."""
    
    def test_schema_file_exists(self):
        """Test that schema file exists."""
        from pathlib import Path
        
        schema_file = Path("graph/schemas/legal_schema.cypher")
        assert schema_file.exists(), "Schema file should exist"
    
    def test_schema_file_readable(self):
        """Test that schema file is readable."""
        from pathlib import Path
        
        schema_file = Path("graph/schemas/legal_schema.cypher")
        
        with open(schema_file) as f:
            content = f.read()
        
        # Check for key schema elements
        assert "Peraturan" in content
        assert "Pasal" in content
        assert "KonsepHukum" in content
        assert "MERUJUK_KE" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
