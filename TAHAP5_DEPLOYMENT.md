# TAHAP 5 FastAPI Deployment Guide

## Overview

TAHAP 5 provides a complete REST API for the LegalKG system using FastAPI. This guide covers deployment options from development to production.

---

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Production Deployment](#production-deployment)
4. [Configuration](#configuration)
5. [Monitoring & Troubleshooting](#monitoring--troubleshooting)

---

## Local Development

### Prerequisites

- Python 3.11+
- Neo4j 5.x (running locally or via Docker)
- API Keys:
  - Google Gemini API Key
  - OpenAI API Key (optional, for embeddings)

### Setup

1. **Create Virtual Environment**

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

2. **Install Dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure Environment**

Create `.env` file in project root:

```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# API Keys
GOOGLE_GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
```

4. **Start Neo4j** (if not already running)

```bash
# Using Docker
docker run -d \
  --name neo4j \
  -p 7687:7687 \
  -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5.15-community
```

5. **Run Development Server**

```bash
# Development mode with auto-reload
python -m api.main

# Or using uvicorn directly
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Docker Deployment

### Single Container (API only)

Requires Neo4j running externally.

```bash
# Build image
docker build -f deployment/Dockerfile.api -t legalkg-api:latest .

# Run container
docker run -d \
  --name legalkg-api \
  -p 8000:8000 \
  -e NEO4J_URI=bolt://host.docker.internal:7687 \
  -e NEO4J_USER=neo4j \
  -e NEO4J_PASSWORD=password \
  -e GOOGLE_GEMINI_API_KEY=your_key \
  -e OPENAI_API_KEY=your_key \
  legalkg-api:latest
```

### Docker Compose (Complete Stack)

Includes API + Neo4j database.

```bash
# Set environment variables
export GOOGLE_GEMINI_API_KEY=your_gemini_key
export OPENAI_API_KEY=your_openai_key

# Start all services
docker-compose -f docker-compose.api.yml up -d

# View logs
docker-compose -f docker-compose.api.yml logs -f api

# Stop services
docker-compose -f docker-compose.api.yml down
```

### Verify Deployment

```bash
# Check services status
docker-compose -f docker-compose.api.yml ps

# Test API
curl http://localhost:8000/health

# View API documentation
# Open: http://localhost:8000/docs
```

---

## Production Deployment

### Prerequisites

- Docker & Docker Compose
- Kubernetes cluster (optional)
- SSL/TLS certificate
- Domain name
- Monitoring tools (Prometheus, etc.)

### Option 1: Docker Compose on VM

1. **Prepare Server**

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

2. **Configure Production Environment**

Create `production.env`:

```bash
# Neo4j
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=secure_password_here

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# API Keys
GOOGLE_GEMINI_API_KEY=your_production_key
OPENAI_API_KEY=your_production_key

# Security
LEGALKG_API_KEY=your_api_key_for_clients
```

3. **Create Production Compose File**

```yaml
# docker-compose.prod.yml
version: "3.9"

services:
  neo4j:
    image: neo4j:5.15-community
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
    volumes:
      - /data/neo4j:/var/lib/neo4j/data
    restart: always
    networks:
      - legalkg

  api:
    image: legalkg-api:prod
    environment:
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USER: ${NEO4J_USER}
      NEO4J_PASSWORD: ${NEO4J_PASSWORD}
      GOOGLE_GEMINI_API_KEY: ${GOOGLE_GEMINI_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    restart: always
    networks:
      - legalkg

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - /etc/letsencrypt:/etc/letsencrypt
    depends_on:
      - api
    networks:
      - legalkg

networks:
  legalkg:
    driver: bridge
```

4. **Setup Nginx Reverse Proxy**

```nginx
# nginx.conf
upstream api {
    server api:8000;
}

server {
    listen 80;
    server_name api.example.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;
    
    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;
    
    # CORS headers
    add_header 'Access-Control-Allow-Origin' '*' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;
    
    # Security headers
    add_header 'Strict-Transport-Security' 'max-age=31536000; includeSubDomains' always;
    add_header 'X-Content-Type-Options' 'nosniff' always;
    
    # Compression
    gzip on;
    gzip_types text/plain application/json;
    
    location / {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

5. **Deploy**

```bash
# Load environment
export $(cat production.env | xargs)

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Verify
curl -k https://api.example.com/health
```

### Option 2: Kubernetes Deployment

1. **Create Kubernetes Manifests**

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: legalkg

---
# k8s/neo4j-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: neo4j
  namespace: legalkg
spec:
  replicas: 1
  selector:
    matchLabels:
      app: neo4j
  template:
    metadata:
      labels:
        app: neo4j
    spec:
      containers:
      - name: neo4j
        image: neo4j:5.15-community
        ports:
        - containerPort: 7687
        - containerPort: 7474
        env:
        - name: NEO4J_AUTH
          valueFrom:
            secretKeyRef:
              name: neo4j-secret
              key: password
        volumeMounts:
        - name: data
          mountPath: /var/lib/neo4j/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: neo4j-pvc

---
# k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: legalkg-api
  namespace: legalkg
spec:
  replicas: 3
  selector:
    matchLabels:
      app: legalkg-api
  template:
    metadata:
      labels:
        app: legalkg-api
    spec:
      containers:
      - name: api
        image: legalkg-api:prod
        ports:
        - containerPort: 8000
        env:
        - name: NEO4J_URI
          value: "bolt://neo4j:7687"
        - name: GOOGLE_GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secret
              key: gemini_key
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secret
              key: openai_key
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
# k8s/api-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: legalkg-api
  namespace: legalkg
spec:
  selector:
    app: legalkg-api
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

2. **Deploy to Kubernetes**

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets
kubectl create secret generic api-secret \
  --from-literal=gemini_key=$GOOGLE_GEMINI_API_KEY \
  --from-literal=openai_key=$OPENAI_API_KEY \
  -n legalkg

# Deploy services
kubectl apply -f k8s/

# Check status
kubectl get pods -n legalkg
kubectl get svc -n legalkg
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| NEO4J_URI | Yes | - | Neo4j connection URI |
| NEO4J_USER | Yes | neo4j | Neo4j username |
| NEO4J_PASSWORD | Yes | - | Neo4j password |
| GOOGLE_GEMINI_API_KEY | Yes | - | Google Gemini API key |
| OPENAI_API_KEY | No | - | OpenAI API key |
| API_HOST | No | 0.0.0.0 | API bind address |
| API_PORT | No | 8000 | API port |
| DEBUG | No | false | Debug mode |
| LEGALKG_API_KEY | No | - | API key for rate limiting |

### Performance Tuning

1. **Connection Pooling**

```python
# Increase Neo4j pool size
from graph.neo4j_client import Neo4jConfig

config = Neo4jConfig(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password",
    max_connection_pool_size=100,
)
```

2. **Uvicorn Workers**

```bash
# Run with multiple workers
gunicorn api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

3. **Caching**

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_concept_cache(concept_name: str):
    return fetch_from_graph(concept_name)
```

---

## Monitoring & Troubleshooting

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Detailed stats
curl http://localhost:8000/api/v1/stats

# Component status
curl http://localhost:8000/api/v1/components
```

### Logs

```bash
# Docker Compose logs
docker-compose -f docker-compose.api.yml logs -f api

# Kubernetes logs
kubectl logs -f deployment/legalkg-api -n legalkg

# View error logs
docker-compose -f docker-compose.api.yml logs api | grep ERROR
```

### Performance Monitoring

```bash
# Monitor requests
curl http://localhost:8000/api/v1/stats | jq '.components'

# Neo4j performance
# Access at http://localhost:7474/browser
```

### Common Issues

1. **Neo4j Connection Failed**

```bash
# Check Neo4j status
docker ps | grep neo4j

# Check connectivity
telnet localhost 7687

# Verify credentials
cypher-shell -u neo4j -p password
```

2. **API Port Already in Use**

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
API_PORT=8001 python -m api.main
```

3. **Rate Limiting Issues**

```python
# Adjust rate limit
from api.middleware import RateLimitMiddleware

# Custom middleware in main.py
app.add_middleware(RateLimitMiddleware, requests_per_minute=120)
```

4. **Memory Issues**

```bash
# Check memory usage
docker stats legalkg-api

# Increase container memory
docker update --memory=4g legalkg-api

# Or in docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 4G
```

---

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.prod.yml
services:
  api:
    deploy:
      replicas: 3
    environment:
      WORKERS: 4
```

### Load Balancing

```bash
# Using Nginx upstream
upstream api_backend {
    server api1:8000;
    server api2:8000;
    server api3:8000;
}

server {
    location / {
        proxy_pass http://api_backend;
    }
}
```

---

## Backup & Recovery

### Database Backup

```bash
# Backup Neo4j
docker exec neo4j neo4j-admin database dump neo4j /backups/neo4j.dump

# Restore from backup
docker exec neo4j neo4j-admin database load neo4j /backups/neo4j.dump
```

### Automated Backups

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/data/backups"
DATE=$(date +%Y%m%d_%H%M%S)

docker exec neo4j neo4j-admin database dump neo4j \
  "$BACKUP_DIR/neo4j_$DATE.dump"

# Keep last 7 days
find $BACKUP_DIR -name "neo4j_*.dump" -mtime +7 -delete
```

---

## Support & Resources

- **API Docs**: http://localhost:8000/docs
- **FastAPI**: https://fastapi.tiangolo.com/
- **Docker Docs**: https://docs.docker.com/
- **Neo4j Docs**: https://neo4j.com/docs/
- **Kubernetes**: https://kubernetes.io/docs/
