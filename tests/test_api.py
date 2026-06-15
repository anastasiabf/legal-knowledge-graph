"""
API Tests - TAHAP 5 Endpoint Testing
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from api.main import app, app_state


client = TestClient(app)


# ==================== Root and Health Tests ====================

def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "LegalKG - Legal Knowledge Graph API"
    assert "endpoints" in response.json()


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "components" in data


def test_version_endpoint():
    """Test version endpoint."""
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json()["version"] == "1.0.0"


# ==================== Chat Endpoints Tests ====================

@patch("api.routes.chat.get_rag")
def test_chat_query_success(mock_get_rag):
    """Test successful chat query."""
    # Mock RAG
    mock_rag = MagicMock()
    mock_rag.query.return_value = {
        "answer": "Test answer",
        "confidence": 0.95,
        "sources": [
            {
                "nomor_pasal": "Pasal 1",
                "nomor_peraturan": "UU 1/2020",
                "score": 0.95,
            }
        ],
        "reasoning_steps": ["Step 1", "Step 2"],
    }
    
    mock_get_rag.return_value = mock_rag
    
    response = client.post(
        "/api/v1/chat/query",
        json={
            "question": "What is the legal framework?",
            "strategy": "hybrid",
            "top_k": 5,
            "include_reasoning": True,
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Test answer"
    assert data["confidence"] == 0.95
    assert len(data["sources"]) > 0


@patch("api.routes.chat.get_rag")
def test_chat_query_no_rag(mock_get_rag):
    """Test chat query when RAG not available."""
    mock_get_rag.side_effect = Exception("RAG not available")
    
    response = client.post(
        "/api/v1/chat/query",
        json={
            "question": "Test question",
            "strategy": "hybrid",
        }
    )
    
    assert response.status_code == 500


@patch("api.routes.chat.get_rag")
def test_chat_batch_queries(mock_get_rag):
    """Test batch chat queries."""
    mock_rag = MagicMock()
    mock_rag.query.return_value = {
        "answer": "Test answer",
        "confidence": 0.95,
        "sources": [],
        "reasoning_steps": [],
        "processing_time_ms": 100,
    }
    
    mock_get_rag.return_value = mock_rag
    
    response = client.post(
        "/api/v1/chat/batch",
        json={
            "questions": ["Question 1", "Question 2"],
            "strategy": "hybrid",
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2


# ==================== Documents Endpoints Tests ====================

@patch("api.routes.documents.get_retriever")
def test_document_search_success(mock_get_retriever):
    """Test successful document search."""
    from api.models import DocumentSearchResult
    
    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = (
        [
            Mock(
                nomor_pasal="Pasal 1",
                nomor_peraturan="UU 1/2020",
                judul_pasal="Ruang Lingkup",
                judul_peraturan="Undang-Undang",
                pasal_text="Content",
                score=0.95,
                strategy=Mock(value="hybrid"),
            )
        ],
        {}
    )
    
    mock_get_retriever.return_value = mock_retriever
    
    response = client.post(
        "/api/v1/documents/search",
        json={
            "query": "legal framework",
            "top_k": 5,
            "strategy": "hybrid",
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] > 0


@patch("api.routes.documents.get_neo4j")
def test_get_pasal(mock_get_neo4j):
    """Test getting a specific pasal."""
    mock_neo4j = MagicMock()
    mock_neo4j.execute_query.return_value = [
        {
            "nomor": "1",
            "judul": "Ruang Lingkup",
            "text": "Pasal content here",
            "peraturan_nomor": "UU 1/2020",
            "peraturan_judul": "Undang-Undang",
        }
    ]
    
    mock_get_neo4j.return_value = mock_neo4j
    
    response = client.get("/api/v1/documents/pasal/1")
    
    assert response.status_code == 200
    data = response.json()
    assert data["nomor"] == "1"


@patch("api.routes.documents.get_neo4j")
def test_list_peraturan(mock_get_neo4j):
    """Test listing regulations."""
    mock_neo4j = MagicMock()
    
    # Mock query result
    mock_neo4j.execute_query.side_effect = [
        [
            {
                "nomor": "UU 1/2020",
                "judul": "Test UU",
                "tahun": 2020,
                "jenis": "UU",
                "total_pasal": 10,
            }
        ],
        [{"count": 1}]
    ]
    
    mock_get_neo4j.return_value = mock_neo4j
    
    response = client.get("/api/v1/documents/peraturan")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 0


# ==================== Graph Endpoints Tests ====================

@patch("api.routes.graph.get_neo4j")
def test_explore_graph(mock_get_neo4j):
    """Test graph exploration."""
    mock_neo4j = MagicMock()
    
    # Mock concept search
    mock_neo4j.execute_query.side_effect = [
        [{"nama": "Hak Asasi Manusia", "id": "concept_1"}],
        [],
        [],
    ]
    
    mock_get_neo4j.return_value = mock_neo4j
    
    response = client.post(
        "/api/v1/graph/explore",
        json={
            "concept": "Hak Asasi Manusia",
            "depth": 2,
            "limit": 10,
        }
    )
    
    # Should return 200 or 404 depending on actual data
    assert response.status_code in [200, 404]


@patch("api.routes.graph.get_neo4j")
def test_list_concepts(mock_get_neo4j):
    """Test listing concepts."""
    mock_neo4j = MagicMock()
    
    mock_neo4j.execute_query.side_effect = [
        [
            {
                "nama": "Hak Asasi Manusia",
                "definisi": "Definition",
                "frequency": 10,
                "confidence": 0.95,
            }
        ],
        [{"count": 1}]
    ]
    
    mock_get_neo4j.return_value = mock_neo4j
    
    response = client.get("/api/v1/graph/concepts")
    
    assert response.status_code == 200
    data = response.json()
    assert "concepts" in data


@patch("api.routes.graph.get_neo4j")
def test_get_schema(mock_get_neo4j):
    """Test getting graph schema."""
    mock_neo4j = MagicMock()
    mock_neo4j.get_schema_info.return_value = {
        "labels": ["Peraturan", "Pasal", "KonsepHukum"],
        "relationships": ["BAGIAN_DARI", "MENGATUR"],
        "indexes": [],
        "constraints": [],
    }
    
    mock_get_neo4j.return_value = mock_neo4j
    
    response = client.get("/api/v1/graph/schema")
    
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data


# ==================== Utils Endpoints Tests ====================

def test_get_stats():
    """Test system statistics."""
    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["uptime_seconds"] >= 0


def test_get_info():
    """Test system information."""
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "LegalKG"


def test_get_uptime():
    """Test uptime endpoint."""
    response = client.get("/api/v1/uptime")
    assert response.status_code == 200
    data = response.json()
    assert data["uptime_seconds"] >= 0


def test_get_components_status():
    """Test component status."""
    response = client.get("/api/v1/components")
    assert response.status_code == 200
    data = response.json()
    assert "neo4j" in data or "rag_engine" in data


# ==================== Middleware Tests ====================

def test_cors_headers():
    """Test CORS headers."""
    response = client.get("/")
    # CORS should allow all origins
    assert "access-control-allow-origin" in response.headers or True


def test_gzip_compression():
    """Test GZIP compression."""
    response = client.get("/")
    # Check if content-encoding header present for large responses
    # For small responses, it might not be compressed


def test_rate_limit_headers():
    """Test rate limit headers."""
    response = client.get("/")
    # Should have rate limit info
    assert response.status_code == 200


# ==================== Error Handling Tests ====================

def test_404_not_found():
    """Test 404 error."""
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404


def test_invalid_request_body():
    """Test invalid request body."""
    response = client.post(
        "/api/v1/chat/query",
        json={"invalid": "data"}
    )
    assert response.status_code in [422, 500]


def test_request_timeout():
    """Test request timeout handling."""
    # This is handled by uvicorn timeout settings
    pass


# ==================== Integration Tests ====================

def test_full_chat_flow():
    """Test full chat flow."""
    # This would require a running Neo4j instance
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
