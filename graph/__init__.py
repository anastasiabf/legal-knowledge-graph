"""
TAHAP 3: Graph Configuration & Loading

Neo4j integration module for LegalKG platform.
Handles graph schema, loading, and vector indexing.
"""

from graph.neo4j_client import Neo4jClient
from graph.graph_loader import GraphLoader
from graph.vector_manager import VectorManager

__all__ = ["Neo4jClient", "GraphLoader", "VectorManager"]
