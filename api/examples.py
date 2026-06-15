"""
API Usage Examples - TAHAP 5 FastAPI
Complete examples for all API endpoints
"""

import requests
import json
from typing import List, Dict


# API Configuration
API_BASE_URL = "http://localhost:8000"
API_VERSION = "v1"


class LegalKGClient:
    """Python client for LegalKG API."""
    
    def __init__(self, base_url: str = API_BASE_URL, api_key: str = None):
        """
        Initialize client.
        
        Args:
            base_url: API base URL
            api_key: Optional API key
        """
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def _request(self, method: str, path: str, **kwargs) -> Dict:
        """Make HTTP request."""
        url = f"{self.base_url}/api/{API_VERSION}{path}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    # Chat Endpoints
    
    def query(self, question: str, strategy: str = "hybrid", top_k: int = 5) -> Dict:
        """
        Ask a single question.
        
        Example:
            client.query("Apa definisi hak asasi manusia?")
        """
        return self._request("POST", "/chat/query", json={
            "question": question,
            "strategy": strategy,
            "top_k": top_k,
            "include_reasoning": True,
            "max_context_tokens": 4000,
        })
    
    def batch_query(self, questions: List[str], strategy: str = "hybrid") -> Dict:
        """
        Ask multiple questions in batch.
        
        Example:
            client.batch_query(["Question 1", "Question 2"])
        """
        return self._request("POST", "/chat/batch", json={
            "questions": questions,
            "strategy": strategy,
            "parallel": False,
        })
    
    # Document Endpoints
    
    def search_documents(self, query: str, strategy: str = "hybrid", top_k: int = 5) -> Dict:
        """
        Search for documents.
        
        Example:
            client.search_documents("hak asasi manusia")
        """
        return self._request("POST", "/documents/search", json={
            "query": query,
            "top_k": top_k,
            "strategy": strategy,
        })
    
    def get_pasal(self, nomor: str) -> Dict:
        """
        Get specific pasal.
        
        Example:
            client.get_pasal("1")
        """
        return self._request("GET", f"/documents/pasal/{nomor}")
    
    def list_peraturan(self, skip: int = 0, limit: int = 10) -> Dict:
        """
        List all regulations.
        
        Example:
            client.list_peraturan()
        """
        return self._request("GET", f"/documents/peraturan?skip={skip}&limit={limit}")
    
    # Graph Endpoints
    
    def explore_graph(self, concept: str, depth: int = 2, limit: int = 10) -> Dict:
        """
        Explore graph around concept.
        
        Example:
            client.explore_graph("Hak Asasi Manusia")
        """
        return self._request("POST", "/graph/explore", json={
            "concept": concept,
            "depth": depth,
            "limit": limit,
        })
    
    def list_concepts(self, skip: int = 0, limit: int = 20) -> Dict:
        """
        List all concepts.
        
        Example:
            client.list_concepts()
        """
        return self._request("GET", f"/graph/concepts?skip={skip}&limit={limit}")
    
    def get_schema(self) -> Dict:
        """Get graph schema."""
        return self._request("GET", "/graph/schema")
    
    def get_statistics(self) -> Dict:
        """Get graph statistics."""
        return self._request("GET", "/graph/statistics")
    
    # Utils Endpoints
    
    def get_stats(self) -> Dict:
        """Get system statistics."""
        return self._request("GET", "/stats")
    
    def get_info(self) -> Dict:
        """Get system info."""
        return self._request("GET", "/info")
    
    def get_health(self) -> Dict:
        """Get health status."""
        return self._request("GET", "/health")
    
    def get_uptime(self) -> Dict:
        """Get uptime."""
        return self._request("GET", "/uptime")
    
    def get_components(self) -> Dict:
        """Get component status."""
        return self._request("GET", "/components")


# ============================================
# Example Usage Functions
# ============================================

def example_1_basic_query():
    """Example 1: Basic Q&A query."""
    print("\n=== Example 1: Basic Q&A Query ===")
    
    client = LegalKGClient()
    
    result = client.query(
        question="Apa yang dimaksud dengan hak asasi manusia?",
        strategy="hybrid",
        top_k=5
    )
    
    print(f"Question: {result}")
    print(f"Answer: {result['answer']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Processing Time: {result['processing_time_ms']:.0f}ms")
    
    if result['sources']:
        print("\nSources:")
        for source in result['sources']:
            print(f"  - {source['nomor_pasal']} ({source['nomor_peraturan']})")


def example_2_document_search():
    """Example 2: Document search."""
    print("\n=== Example 2: Document Search ===")
    
    client = LegalKGClient()
    
    results = client.search_documents(
        query="hak asasi manusia",
        top_k=10
    )
    
    print(f"Found {results['total_results']} results")
    print(f"Processing time: {results['processing_time_ms']:.0f}ms\n")
    
    for i, result in enumerate(results['results'][:5], 1):
        print(f"{i}. {result['nomor_pasal']} - {result['judul_pasal']}")
        print(f"   Peraturan: {result['nomor_peraturan']}")
        print(f"   Score: {result['score']:.2%}")
        print()


def example_3_batch_queries():
    """Example 3: Batch queries."""
    print("\n=== Example 3: Batch Queries ===")
    
    client = LegalKGClient()
    
    questions = [
        "Apa definisi hak asasi manusia?",
        "Siapa yang berwenang mengawasi pelaksanaan HAM?",
        "Bagaimana mekanisme perlindungan HAM?",
    ]
    
    results = client.batch_query(questions)
    
    print(f"Processed {len(results['results'])} questions")
    print(f"Total time: {results['total_time_ms']:.0f}ms")
    print(f"Failed: {results['failed_count']}\n")
    
    for i, result in enumerate(results['results'], 1):
        print(f"{i}. Confidence: {result['confidence']:.2%}")
        print(f"   Time: {result['processing_time_ms']:.0f}ms")


def example_4_graph_exploration():
    """Example 4: Graph exploration."""
    print("\n=== Example 4: Graph Exploration ===")
    
    client = LegalKGClient()
    
    result = client.explore_graph(
        concept="Hak Asasi Manusia",
        depth=2,
        limit=20
    )
    
    print(f"Center Concept: {result['center_node']}")
    print(f"Nodes: {len(result['nodes'])}")
    print(f"Edges: {len(result['edges'])}\n")
    
    print("Related Concepts:")
    for node in result['nodes'][:5]:
        print(f"  - {node['label']} ({node['type']})")


def example_5_concept_listing():
    """Example 5: List all concepts."""
    print("\n=== Example 5: Concept Listing ===")
    
    client = LegalKGClient()
    
    result = client.list_concepts(limit=10)
    
    print(f"Total concepts: {result['total']}")
    print(f"Showing {len(result['concepts'])} concepts\n")
    
    for concept in result['concepts']:
        print(f"- {concept['nama']}")
        print(f"  Frequency: {concept['frequency']}")
        print(f"  Confidence: {concept['confidence']:.2%}")


def example_6_system_monitoring():
    """Example 6: System monitoring."""
    print("\n=== Example 6: System Monitoring ===")
    
    client = LegalKGClient()
    
    # Get health
    health = client.get_health()
    print("Health Status:")
    print(f"  Overall: {health['status']}")
    print(f"  Neo4j: {health['components']['neo4j']}")
    print(f"  RAG: {health['components']['rag']}\n")
    
    # Get stats
    stats = client.get_stats()
    print("Statistics:")
    print(f"  Uptime: {stats['uptime_seconds']:.0f}s")
    print(f"  Total Queries: {stats['total_queries']}")
    print(f"  Neo4j: {stats['neo4j_status']}")
    print(f"  RAG: {stats['rag_status']}\n")
    
    # Get info
    info = client.get_info()
    print("System Info:")
    print(f"  Version: {info['version']}")
    print(f"  Phase: {info['phase']}")


def example_7_pasal_retrieval():
    """Example 7: Get specific pasal."""
    print("\n=== Example 7: Pasal Retrieval ===")
    
    client = LegalKGClient()
    
    result = client.get_pasal("1")
    
    print(f"Nomor: {result['nomor']}")
    print(f"Judul: {result['judul']}")
    print(f"Peraturan: {result['peraturan']['nomor']}")
    print(f"\nText:\n{result['text'][:200]}...")


def example_8_peraturan_listing():
    """Example 8: List regulations."""
    print("\n=== Example 8: Regulation Listing ===")
    
    client = LegalKGClient()
    
    result = client.list_peraturan(limit=5)
    
    print(f"Total Regulations: {result['total']}\n")
    
    for peraturan in result['results']:
        print(f"- {peraturan['nomor']}")
        print(f"  Judul: {peraturan['judul']}")
        print(f"  Tahun: {peraturan['tahun']}")
        print(f"  Jenis: {peraturan['jenis']}")
        print(f"  Total Pasal: {peraturan['total_pasal']}")


def example_9_graph_statistics():
    """Example 9: Graph statistics."""
    print("\n=== Example 9: Graph Statistics ===")
    
    client = LegalKGClient()
    
    stats = client.get_statistics()
    
    print("Graph Statistics:")
    for key, value in stats['graph_statistics'].items():
        print(f"  {key}: {value}")


def example_10_advanced_search():
    """Example 10: Advanced search with different strategies."""
    print("\n=== Example 10: Advanced Search ===")
    
    client = LegalKGClient()
    
    query = "hak asasi manusia"
    strategies = ["vector", "graph", "bm25", "hybrid"]
    
    print(f"Searching for: '{query}'\n")
    
    for strategy in strategies:
        try:
            result = client.search_documents(
                query=query,
                strategy=strategy,
                top_k=3
            )
            
            print(f"{strategy.upper()}:")
            print(f"  Results: {result['total_results']}")
            print(f"  Time: {result['processing_time_ms']:.0f}ms")
            print()
            
        except Exception as e:
            print(f"{strategy.upper()}: Error - {e}\n")


# ============================================
# Raw HTTP Examples (using curl)
# ============================================

CURL_EXAMPLES = """
# ============================================
# cURL Examples
# ============================================

# 1. Basic Query
curl -X POST http://localhost:8000/api/v1/chat/query \\
  -H "Content-Type: application/json" \\
  -d '{
    "question": "Apa definisi hak asasi manusia?",
    "strategy": "hybrid",
    "top_k": 5
  }'

# 2. Batch Queries
curl -X POST http://localhost:8000/api/v1/chat/batch \\
  -H "Content-Type: application/json" \\
  -d '{
    "questions": ["Question 1", "Question 2"],
    "strategy": "hybrid"
  }'

# 3. Document Search
curl -X POST http://localhost:8000/api/v1/documents/search \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "hak asasi manusia",
    "top_k": 10,
    "strategy": "hybrid"
  }'

# 4. Get Pasal
curl -X GET http://localhost:8000/api/v1/documents/pasal/1

# 5. List Regulations
curl -X GET "http://localhost:8000/api/v1/documents/peraturan?skip=0&limit=10"

# 6. Explore Graph
curl -X POST http://localhost:8000/api/v1/graph/explore \\
  -H "Content-Type: application/json" \\
  -d '{
    "concept": "Hak Asasi Manusia",
    "depth": 2,
    "limit": 10
  }'

# 7. List Concepts
curl -X GET "http://localhost:8000/api/v1/graph/concepts?skip=0&limit=20"

# 8. Get Schema
curl -X GET http://localhost:8000/api/v1/graph/schema

# 9. Get Health
curl -X GET http://localhost:8000/health

# 10. Get Stats
curl -X GET http://localhost:8000/api/v1/stats

# 11. Get Uptime
curl -X GET http://localhost:8000/api/v1/uptime

# 12. Get System Info
curl -X GET http://localhost:8000/api/v1/info

# 13. Get Components Status
curl -X GET http://localhost:8000/api/v1/components
"""


if __name__ == "__main__":
    print("LegalKG API Examples")
    print("=" * 50)
    
    try:
        # Run all examples
        example_1_basic_query()
        example_2_document_search()
        example_3_batch_queries()
        example_4_graph_exploration()
        example_5_concept_listing()
        example_6_system_monitoring()
        example_7_pasal_retrieval()
        example_8_peraturan_listing()
        example_9_graph_statistics()
        example_10_advanced_search()
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API at", API_BASE_URL)
        print("Make sure the API is running: python -m api.main")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + CURL_EXAMPLES)
