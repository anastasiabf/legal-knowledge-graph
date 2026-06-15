# LegalKG FastAPI - Complete API Documentation

## Overview

LegalKG is a comprehensive Legal Knowledge Graph platform with a FastAPI REST API (TAHAP 5) that provides access to:

- **Chat Q&A Engine**: Ask questions about legal documents
- **Document Search**: Search through regulations and legal documents
- **Graph Exploration**: Navigate legal concepts and relationships
- **System Management**: Monitor health and statistics

---

## Getting Started

### Prerequisites

- Python 3.11+
- Neo4j 5.x running
- Google Gemini API Key
- OpenAI API Key (for embeddings)

### Installation

```bash
# Clone repository
cd legal-kg

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GOOGLE_GEMINI_API_KEY="your-key"
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your-password"
export OPENAI_API_KEY="your-key"
```

### Running the API

```bash
# Development mode
python -m api.main

# Production mode
uvicorn api.main:app --host 0.0.0.0 --port 8000

# With custom settings
API_HOST=0.0.0.0 API_PORT=8000 DEBUG=false python -m api.main
```

The API will be available at:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## API Endpoints

### Root & Health

#### `GET /`
Root endpoint with system information.

**Response:**
```json
{
  "name": "LegalKG API",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {
    "chat": "/api/v1/chat",
    "documents": "/api/v1/documents",
    "graph": "/api/v1/graph",
    "health": "/api/v1/health"
  }
}
```

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "neo4j": "connected",
  "rag": "ready",
  "vector_manager": "ready"
}
```

#### `GET /version`
Get API version.

**Response:**
```json
{
  "api": "1.0.0",
  "phase": "TAHAP 5 - FastAPI REST API"
}
```

---

### Chat Endpoints

#### `POST /api/v1/chat/query`
Ask a single question about legal documents.

**Request:**
```json
{
  "question": "Apa definisi hak asasi manusia?",
  "strategy": "hybrid",
  "top_k": 5,
  "include_reasoning": true,
  "max_context_tokens": 4000
}
```

**Parameters:**
- `question` (string, required): The question to ask
- `strategy` (enum, optional): Retrieval strategy - `vector`, `graph`, `bm25`, or `hybrid`
- `top_k` (integer, optional): Number of documents to retrieve (1-20)
- `include_reasoning` (boolean, optional): Include chain-of-thought reasoning
- `max_context_tokens` (integer, optional): Maximum context size (1000-10000)

**Response:**
```json
{
  "answer": "Hak asasi manusia adalah...",
  "confidence": 0.95,
  "sources": [
    {
      "nomor_pasal": "Pasal 1",
      "nomor_peraturan": "UU 39/1999",
      "score": 0.95
    }
  ],
  "reasoning_steps": [
    "Step 1: Searching for relevant regulations...",
    "Step 2: Analyzing legal concepts..."
  ],
  "processing_time_ms": 245.5,
  "model": "gemini-1.5-pro"
}
```

#### `POST /api/v1/chat/batch`
Process multiple questions in batch.

**Request:**
```json
{
  "questions": [
    "Pertanyaan 1?",
    "Pertanyaan 2?"
  ],
  "strategy": "hybrid",
  "parallel": false
}
```

**Response:**
```json
{
  "results": [
    {
      "answer": "Jawaban 1...",
      "confidence": 0.92,
      "sources": [],
      "reasoning_steps": [],
      "processing_time_ms": 250
    },
    {
      "answer": "Jawaban 2...",
      "confidence": 0.88,
      "sources": [],
      "reasoning_steps": [],
      "processing_time_ms": 220
    }
  ],
  "total_time_ms": 470,
  "failed_count": 0
}
```

#### `GET /api/v1/chat/health`
Check chat service health.

**Response:**
```json
{
  "status": "healthy",
  "rag_available": true
}
```

---

### Document Endpoints

#### `POST /api/v1/documents/search`
Search for legal documents.

**Request:**
```json
{
  "query": "hak asasi manusia",
  "top_k": 10,
  "strategy": "hybrid"
}
```

**Response:**
```json
{
  "results": [
    {
      "nomor_pasal": "Pasal 1",
      "nomor_peraturan": "UU 39/1999",
      "judul_pasal": "Ruang Lingkup",
      "judul_peraturan": "Undang-Undang Hak Asasi Manusia",
      "pasal_text": "...",
      "score": 0.95,
      "strategy": "hybrid"
    }
  ],
  "total_results": 42,
  "processing_time_ms": 185.3
}
```

#### `GET /api/v1/documents/pasal/{nomor}`
Get a specific pasal by number.

**Response:**
```json
{
  "nomor": "1",
  "judul": "Ruang Lingkup",
  "text": "Pasal content...",
  "peraturan": {
    "nomor": "UU 39/1999",
    "judul": "Undang-Undang Hak Asasi Manusia"
  }
}
```

#### `GET /api/v1/documents/peraturan`
List all regulations.

**Query Parameters:**
- `skip` (integer, optional): Skip N records (default: 0)
- `limit` (integer, optional): Max results (default: 10, max: 100)

**Response:**
```json
{
  "total": 500,
  "skip": 0,
  "limit": 10,
  "results": [
    {
      "nomor": "UU 1/2020",
      "judul": "Undang-Undang...",
      "tahun": 2020,
      "jenis": "UU",
      "total_pasal": 150
    }
  ]
}
```

#### `POST /api/v1/documents/ingest`
Ingest a new document (beta).

**Request:**
```json
{
  "file_url": "http://example.com/document.pdf",
  "metadata": {
    "source": "bpk.go.id"
  }
}
```

**Response:**
```json
{
  "status": "queued",
  "document_id": "doc_123",
  "message": "Document queued for processing"
}
```

#### `GET /api/v1/documents/ingest/{document_id}`
Get document ingestion status.

**Response:**
```json
{
  "document_id": "doc_123",
  "status": "completed",
  "message": "Document successfully processed"
}
```

---

### Graph Endpoints

#### `POST /api/v1/graph/explore`
Explore the graph around a legal concept.

**Request:**
```json
{
  "concept": "Hak Asasi Manusia",
  "depth": 2,
  "limit": 20
}
```

**Parameters:**
- `concept` (string, required): Legal concept to explore
- `depth` (integer, optional): Traversal depth (1-5)
- `limit` (integer, optional): Max nodes to return (1-100)

**Response:**
```json
{
  "nodes": [
    {
      "id": "concept_1",
      "label": "Hak Asasi Manusia",
      "type": "KonsepHukum",
      "properties": {
        "definisi": "...",
        "frequency": 45,
        "confidence": 0.95
      }
    }
  ],
  "edges": [
    {
      "source": "concept_1",
      "target": "pasal_1",
      "type": "MENGATUR",
      "properties": {}
    }
  ],
  "center_node": "Hak Asasi Manusia"
}
```

#### `GET /api/v1/graph/concepts`
List all legal concepts.

**Query Parameters:**
- `skip` (integer, optional): Skip N records
- `limit` (integer, optional): Max results (1-100)

**Response:**
```json
{
  "total": 1250,
  "skip": 0,
  "limit": 20,
  "concepts": [
    {
      "nama": "Hak Asasi Manusia",
      "definisi": "Definition...",
      "frequency": 45,
      "confidence": 0.95
    }
  ]
}
```

#### `GET /api/v1/graph/schema`
Get graph schema information.

**Response:**
```json
{
  "nodes": [
    "Peraturan",
    "Pasal",
    "Ayat",
    "KonsepHukum",
    "Lembaga"
  ],
  "relationships": [
    "BAGIAN_DARI",
    "MERUJUK_KE",
    "MENGATUR",
    "MENCABUT",
    "MENGUBAH",
    "DASAR_DELEGASI",
    "PENERBIT_OLEH"
  ],
  "indexes": [],
  "constraints": []
}
```

#### `GET /api/v1/graph/statistics`
Get graph statistics.

**Response:**
```json
{
  "graph_statistics": {
    "peraturan": 500,
    "pasal": 5000,
    "ayat": 15000,
    "konsep_hukum": 1250
  },
  "timestamp": "2024-01-15T10:30:00"
}
```

---

### Utility Endpoints

#### `GET /api/v1/stats`
Get system statistics.

**Response:**
```json
{
  "uptime_seconds": 3600,
  "total_queries": 245,
  "neo4j_status": "healthy",
  "rag_status": "healthy",
  "components": {
    "retriever": {
      "total_operations": 245,
      "average_time_ms": 150
    },
    "context_manager": {
      "total_operations": 245,
      "average_time_ms": 50
    },
    "reasoner": {
      "total_operations": 245,
      "average_time_ms": 0,
      "total_tokens": 125000
    }
  }
}
```

#### `GET /api/v1/info`
Get system information.

**Response:**
```json
{
  "name": "LegalKG",
  "description": "Legal Knowledge Graph & Regulatory Intelligence Platform",
  "version": "1.0.0",
  "phase": "TAHAP 5 - FastAPI REST API",
  "components": {
    "tahap_1": {"name": "Ingestion & Scraping", "status": "complete"},
    "tahap_2": {"name": "LLM-Powered Extraction", "status": "complete"},
    "tahap_3": {"name": "Graph Configuration", "status": "complete"},
    "tahap_4": {"name": "RAG Engine", "status": "complete"},
    "tahap_5": {"name": "FastAPI REST API", "status": "active"}
  }
}
```

#### `GET /api/v1/uptime`
Get system uptime.

**Response:**
```json
{
  "uptime_seconds": 3600,
  "uptime_formatted": "1h 0m 0s",
  "startup_time": "2024-01-15T09:30:00"
}
```

#### `GET /api/v1/components`
Get component status.

**Response:**
```json
{
  "neo4j": {
    "status": "healthy",
    "type": "Graph Database",
    "version": "5.15.0"
  },
  "vector_manager": {
    "status": "healthy",
    "type": "Embedding & Vector Search",
    "provider": "openai"
  },
  "rag_engine": {
    "status": "healthy",
    "type": "Question Answering",
    "model": "gemini-1.5-pro"
  }
}
```

---

## Usage Examples

### Python Client

```python
from api.examples import LegalKGClient

client = LegalKGClient("http://localhost:8000")

# Ask a question
result = client.query("Apa definisi hak asasi manusia?")
print(result["answer"])

# Search documents
results = client.search_documents("hak asasi manusia", top_k=10)
for doc in results["results"]:
    print(f"- {doc['nomor_pasal']}: {doc['judul_pasal']}")

# Explore graph
graph = client.explore_graph("Hak Asasi Manusia", depth=2)
print(f"Found {len(graph['nodes'])} nodes")

# Get stats
stats = client.get_stats()
print(f"Uptime: {stats['uptime_seconds']} seconds")
```

### cURL

```bash
# Ask a question
curl -X POST http://localhost:8000/api/v1/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Apa definisi hak asasi manusia?",
    "strategy": "hybrid"
  }'

# Search documents
curl -X POST http://localhost:8000/api/v1/documents/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "hak asasi manusia",
    "top_k": 10
  }'

# Get system info
curl http://localhost:8000/api/v1/info
```

### JavaScript/Node.js

```javascript
const API_URL = "http://localhost:8000";

// Ask a question
async function askQuestion(question) {
  const response = await fetch(`${API_URL}/api/v1/chat/query`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      question: question,
      strategy: "hybrid"
    })
  });
  return await response.json();
}

// Search documents
async function searchDocuments(query) {
  const response = await fetch(`${API_URL}/api/v1/documents/search`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      query: query,
      top_k: 10
    })
  });
  return await response.json();
}

// Usage
const result = await askQuestion("Apa definisi hak asasi manusia?");
console.log(result.answer);
```

---

## Rate Limiting

- Default: 60 requests per minute per IP
- Headers returned:
  - `X-RateLimit-Limit`: Max requests per minute
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-Process-Time`: Processing time in seconds

### Handling Rate Limits

```python
# With backoff
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=3, backoff_factor=1.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)
```

---

## Error Handling

### Common Error Responses

#### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

#### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

#### 429 Too Many Requests
```json
{
  "detail": "Too many requests"
}
```

#### 503 Service Unavailable
```json
{
  "detail": "Neo4j connection not available"
}
```

### Retry Strategy

```python
import time
from functools import wraps

def retry_with_backoff(max_retries=3, backoff_factor=1.5):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    wait_time = backoff_factor ** attempt
                    print(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
        return wrapper
    return decorator
```

---

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: "3.9"
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      NEO4J_URI: "bolt://neo4j:7687"
      NEO4J_USER: "neo4j"
      NEO4J_PASSWORD: "password"
      GOOGLE_GEMINI_API_KEY: "${GOOGLE_GEMINI_API_KEY}"
    depends_on:
      - neo4j

  neo4j:
    image: neo4j:5.15
    ports:
      - "7687:7687"
    environment:
      NEO4J_AUTH: "neo4j/password"
```

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=api tests/test_api.py

# Run specific test
pytest tests/test_api.py::test_chat_query_success -v
```

---

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## Support

For issues and questions:
1. Check the Swagger documentation at `/docs`
2. Review error messages and logs
3. Check component status at `/api/v1/components`
4. Review system statistics at `/api/v1/stats`
