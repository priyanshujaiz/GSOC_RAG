# 📡 API Usage Guide

**Live Open-Source Intelligence Platform**  
**Version:** 1.0.0  
**Last Updated:** January 15, 2026

---

## 📋 Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [Base URL](#base-url)
4. [Health & Monitoring](#health--monitoring)
5. [Repository Endpoints](#repository-endpoints)
6. [RAG Chat Endpoints](#rag-chat-endpoints)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)
9. [Code Examples](#code-examples)

---

## 🚀 Getting Started

### **Prerequisites**
- Python 3.10+ (for Python clients)
- API server running on `http://localhost:8000` (or your deployment URL)
- OpenAI API key configured in server environment

### **Quick Start**

```bash
# Start the server
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

# Test basic health
curl http://localhost:8000/health

# Test detailed health
curl http://localhost:8000/api/v1/health
```

---

## 🔐 Authentication

**Current Status:** No authentication required (development mode)

**Production TODO:**
- Add API key authentication via headers: `X-API-Key: your_key_here`
- Or implement OAuth2 for user-based access

---

## 🌐 Base URL

| Environment | Base URL |
|-------------|----------|
| Local Development | `http://localhost:8000` |
| Production | `https://your-domain.com` |

**All endpoints are prefixed with `/api/v1` for versioning.**

---

## 🏥 Health & Monitoring

### **1. Root Endpoint**

**GET** `/`

Returns a welcome message and basic API information.

**Response:**
```json
{
  "message": "Live Open-Source Intelligence API",
  "status": "operational",
  "version": "1.0.0",
  "docs_url": "/docs",
  "health_check": "/health"
}
```

**Example:**
```bash
curl http://localhost:8000/
```

---

### **2. Basic Health Check**

**GET** `/health`

Quick health check for load balancers and monitoring.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-15T10:30:00.123456"
}
```

**Status Codes:**
- `200` - Service is healthy
- `503` - Service is unhealthy

**Example:**
```bash
curl http://localhost:8000/health
```

---

### **3. Detailed Health Check**

**GET** `/api/v1/health`

Comprehensive health check with component status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-15T10:30:00.123456",
  "uptime_seconds": 3600,
  "components": {
    "api": {
      "status": "operational",
      "response_time_ms": 5
    },
    "pathway_pipeline": {
      "status": "running",
      "tables_built": 25,
      "is_processing": true
    },
    "rag_system": {
      "status": "available",
      "query_engine_ready": true,
      "vector_index_built": true
    }
  },
  "health_score": 100
}
```

**Status Values:**
- `healthy` - All systems operational (score ≥ 80)
- `degraded` - Some components issues (score 50-79)
- `unhealthy` - Critical issues (score < 50)

**Example:**
```bash
curl http://localhost:8000/api/v1/health | jq
```

---

### **4. System Metrics**

**GET** `/api/v1/metrics`

Get system-wide metrics and statistics.

**Response:**
```json
{
  "total_events_processed": 1523,
  "active_repositories": 42,
  "total_rag_queries": 89,
  "avg_query_time_ms": 234,
  "websocket_connections": 5,
  "uptime_seconds": 7200,
  "timestamp": "2026-01-15T10:30:00.123456"
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/metrics | jq
```

---

### **5. Readiness Probe**

**GET** `/ready`

Kubernetes readiness probe - checks if service can accept traffic.

**Response:**
```json
{
  "status": "ready",
  "timestamp": "2026-01-15T10:30:00.123456"
}
```

---

### **6. Liveness Probe**

**GET** `/live`

Kubernetes liveness probe - checks if service should be restarted.

**Response:**
```json
{
  "status": "alive",
  "timestamp": "2026-01-15T10:30:00.123456"
}
```

---

## 📊 Repository Endpoints

### **1. Get Top Repositories**

**GET** `/api/v1/repos/top10`

Get the top active repositories ranked by activity score.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 10 | Number of repos to return (1-100) |
| `time_window` | string | No | "24h" | Time window: "1h", "24h", "7d" |

**Response:**
```json
{
  "repositories": [
    {
      "repo_full_name": "openai/openai-python",
      "rank": 1,
      "activity_score": 18.5,
      "trend_status": "🔥 HOT",
      "total_events": 45,
      "event_breakdown": {
        "commits": 23,
        "pull_requests": 12,
        "issues": 8,
        "releases": 2
      },
      "velocity": 2.3,
      "top_contributors": ["alice", "bob", "charlie"],
      "last_event_time": "2026-01-15T10:28:00"
    }
  ],
  "time_window": "24h",
  "timestamp": "2026-01-15T10:30:00.123456"
}
```

**Examples:**

```bash
# Default (top 10 in last 24h)
curl http://localhost:8000/api/v1/repos/top10

# Top 5 in last hour
curl "http://localhost:8000/api/v1/repos/top10?limit=5&time_window=1h"

# Top 20 in last week
curl "http://localhost:8000/api/v1/repos/top10?limit=20&time_window=7d"
```

**Python Example:**
```python
import httpx

async def get_top_repos(limit: int = 10, time_window: str = "24h"):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/repos/top10",
            params={"limit": limit, "time_window": time_window}
        )
        return response.json()

# Usage
repos = await get_top_repos(limit=5, time_window="1h")
for repo in repos["repositories"]:
    print(f"{repo['rank']}. {repo['repo_full_name']} - Score: {repo['activity_score']}")
```

---

### **2. Get Repository Details**

**GET** `/api/v1/repos/{repo_id}`

Get detailed information about a specific repository.

**Path Parameters:**
- `repo_id` (string, required) - Repository identifier (e.g., "openai/openai-python")

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `time_window` | string | No | "24h" | Time window for metrics |

**Response:**
```json
{
  "repo_full_name": "openai/openai-python",
  "activity_score": 18.5,
  "rank": 1,
  "trend_status": "🔥 HOT",
  "momentum": "ACCELERATING",
  "summary": {
    "short": "High activity with 45 events in 24h...",
    "long": "Detailed analysis of repository activity...",
    "key_highlights": [
      "23 commits pushed",
      "12 pull requests opened",
      "Peak activity at 14:00 UTC"
    ]
  },
  "metrics": {
    "total_events": 45,
    "commits": 23,
    "pull_requests": 12,
    "issues": 8,
    "releases": 2,
    "velocity": 2.3,
    "trend": "up"
  },
  "top_contributors": [
    {"username": "alice", "event_count": 15},
    {"username": "bob", "event_count": 12}
  ],
  "recent_events": [...],
  "time_window": "24h",
  "timestamp": "2026-01-15T10:30:00.123456"
}
```

**Examples:**

```bash
# Get details for a specific repo
curl http://localhost:8000/api/v1/repos/openai%2Fopenai-python

# With different time window
curl "http://localhost:8000/api/v1/repos/openai%2Fopenai-python?time_window=7d"
```

**Note:** URL-encode the repo name (replace `/` with `%2F`)

---

### **3. Get Repository Events**

**GET** `/api/v1/repos/{repo_id}/events`

Get recent events for a specific repository.

**Path Parameters:**
- `repo_id` (string, required) - Repository identifier

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 50 | Number of events (1-1000) |
| `event_type` | string | No | null | Filter: "commit", "pull_request", "issue", "release" |
| `since` | string | No | null | ISO timestamp to get events after |

**Response:**
```json
{
  "repo_full_name": "openai/openai-python",
  "events": [
    {
      "event_id": "commit_abc123",
      "event_type": "commit",
      "title": "Fix chat completion bug",
      "author": "alice",
      "timestamp": "2026-01-15T10:25:00",
      "url": "https://github.com/openai/openai-python/commit/abc123",
      "metadata": {
        "additions": 45,
        "deletions": 12,
        "files_changed": 3
      }
    }
  ],
  "total_count": 45,
  "limit": 50,
  "timestamp": "2026-01-15T10:30:00.123456"
}
```

**Examples:**

```bash
# Get last 50 events
curl http://localhost:8000/api/v1/repos/openai%2Fopenai-python/events

# Get last 10 commits only
curl "http://localhost:8000/api/v1/repos/openai%2Fopenai-python/events?limit=10&event_type=commit"

# Get events since specific time
curl "http://localhost:8000/api/v1/repos/openai%2Fopenai-python/events?since=2026-01-15T10:00:00"
```

---

## 💬 RAG Chat Endpoints

### **1. Query RAG System**

**POST** `/api/v1/chat`

Ask natural language questions about repository activity.

**Request Body:**
```json
{
  "query": "Which repositories are most active right now?",
  "max_results": 5,
  "temperature": 0.7,
  "include_sources": true
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | Yes | - | Natural language question (max 500 chars) |
| `max_results` | integer | No | 5 | Number of context chunks to retrieve (1-20) |
| `temperature` | float | No | 0.7 | LLM creativity (0.0-1.0) |
| `include_sources` | boolean | No | true | Include source citations |

**Response:**
```json
{
  "answer": "Based on the latest data, the most active repositories right now are:\n1. **openai/openai-python** - 45 events in the last 24h with high momentum\n2. **langchain-ai/langchain** - 38 events showing strong activity\n3. **pathwaycom/pathway** - 32 events with steady growth",
  "sources": [
    {
      "repo_full_name": "openai/openai-python",
      "content": "High activity with 45 events...",
      "relevance_score": 0.92,
      "metadata": {
        "activity_score": 18.5,
        "trend_status": "🔥 HOT"
      }
    }
  ],
  "confidence": 0.95,
  "query_time_ms": 234,
  "timestamp": "2026-01-15T10:30:00.123456"
}
```

**Examples:**

```bash
# Simple query
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Which repositories are most active?"}'

# Detailed query with options
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What trends are emerging in AI repositories?",
    "max_results": 10,
    "temperature": 0.5
  }'
```

**Python Example:**
```python
import httpx

async def ask_rag(query: str, max_results: int = 5):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/chat",
            json={
                "query": query,
                "max_results": max_results,
                "include_sources": True
            },
            timeout=30.0  # RAG queries can take time
        )
        return response.json()

# Usage
result = await ask_rag("Which repos are trending?")
print(result["answer"])
for source in result["sources"]:
    print(f"  - {source['repo_full_name']} (relevance: {source['relevance_score']})")
```

---

### **2. Batch Query**

**POST** `/api/v1/chat/batch`

Process multiple queries in a single request.

**Request Body:**
```json
{
  "queries": [
    "Which repositories are most active?",
    "What are the trending topics?",
    "Who are the top contributors?"
  ],
  "max_results": 5,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "results": [
    {
      "query": "Which repositories are most active?",
      "answer": "...",
      "sources": [...],
      "confidence": 0.95,
      "query_time_ms": 234
    },
    {
      "query": "What are the trending topics?",
      "answer": "...",
      "sources": [...],
      "confidence": 0.88,
      "query_time_ms": 198
    }
  ],
  "total_time_ms": 432,
  "timestamp": "2026-01-15T10:30:00.123456"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/chat/batch \
  -H "Content-Type: application/json" \
  -d '{
    "queries": [
      "Most active repos?",
      "Trending topics?"
    ]
  }'
```

---

### **3. Get Query Suggestions**

**GET** `/api/v1/chat/suggestions`

Get suggested queries to help users explore the data.

**Response:**
```json
{
  "suggestions": [
    "Which repositories are most active right now?",
    "What are the latest trends in open source?",
    "Who are the top contributors across all repositories?",
    "Which repositories have accelerating activity?",
    "What types of events are most common today?"
  ],
  "categories": {
    "activity": [...],
    "trends": [...],
    "contributors": [...],
    "comparisons": [...]
  }
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/chat/suggestions
```

---

### **4. RAG Health Check**

**GET** `/api/v1/chat/health`

Check if the RAG system is operational.

**Response:**
```json
{
  "status": "operational",
  "query_engine_ready": true,
  "vector_index_built": true,
  "embedding_model": "text-embedding-3-small",
  "llm_model": "gpt-4o-mini",
  "total_documents_indexed": 42,
  "last_index_update": "2026-01-15T10:29:00",
  "timestamp": "2026-01-15T10:30:00.123456"
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/chat/health
```

---

## ❌ Error Handling

### **Standard Error Response**

All errors return a consistent JSON structure:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Query text is required",
    "details": {
      "field": "query",
      "constraint": "min_length",
      "value": ""
    }
  },
  "timestamp": "2026-01-15T10:30:00.123456",
  "request_id": "req_abc123"
}
```

### **HTTP Status Codes**

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid parameters, validation error |
| 404 | Not Found | Repository or endpoint not found |
| 422 | Unprocessable Entity | Pydantic validation failed |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | RAG system not ready, pipeline down |

### **Error Codes**

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Request validation failed |
| `RAG_ERROR` | RAG system error |
| `PIPELINE_ERROR` | Pathway pipeline error |
| `GITHUB_API_ERROR` | GitHub API error |
| `RATE_LIMIT_ERROR` | Rate limit exceeded |

### **Example Error Handling (Python)**

```python
import httpx

async def safe_query(query: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/v1/chat",
                json={"query": query},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    except httpx.HTTPStatusError as e:
        error_data = e.response.json()
        print(f"Error {e.response.status_code}: {error_data['error']['message']}")
        return None
    
    except httpx.RequestError as e:
        print(f"Connection error: {e}")
        return None
```

---

## 🚦 Rate Limiting

**Current Status:** No rate limiting (development mode)

**Production TODO:**
- Implement rate limiting per IP/API key
- Suggested limits:
  - Health endpoints: 100 requests/minute
  - Repository endpoints: 60 requests/minute
  - Chat endpoints: 10 requests/minute (expensive LLM calls)

**Rate Limit Headers (planned):**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1642252800
```

---

## 📝 Code Examples

### **Python with httpx (Recommended)**

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Health check
        health = await client.get("/api/v1/health")
        print(f"Status: {health.json()['status']}")
        
        # Get top repos
        repos = await client.get("/api/v1/repos/top10", params={"limit": 5})
        for repo in repos.json()["repositories"]:
            print(f"  {repo['rank']}. {repo['repo_full_name']}")
        
        # Ask RAG
        chat = await client.post(
            "/api/v1/chat",
            json={"query": "What's happening in AI repos?"}
        )
        print(f"Answer: {chat.json()['answer']}")

asyncio.run(main())
```

### **Python with requests (Sync)**

```python
import requests

base_url = "http://localhost:8000"

# Health check
response = requests.get(f"{base_url}/health")
print(response.json())

# Get top repos
response = requests.get(f"{base_url}/api/v1/repos/top10")
repos = response.json()["repositories"]
for repo in repos:
    print(f"{repo['rank']}. {repo['repo_full_name']} - {repo['activity_score']}")

# RAG query
response = requests.post(
    f"{base_url}/api/v1/chat",
    json={"query": "Which repositories are trending?"},
    timeout=30
)
result = response.json()
print(result["answer"])
```

### **JavaScript/TypeScript (fetch)**

```javascript
const BASE_URL = 'http://localhost:8000';

async function getTopRepos(limit = 10) {
  const response = await fetch(
    `${BASE_URL}/api/v1/repos/top10?limit=${limit}`
  );
  const data = await response.json();
  return data.repositories;
}

async function askRAG(query) {
  const response = await fetch(`${BASE_URL}/api/v1/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query })
  });
  const data = await response.json();
  return data.answer;
}

// Usage
const repos = await getTopRepos(5);
console.log('Top 5 repos:', repos);

const answer = await askRAG('What are the trending topics?');
console.log('Answer:', answer);
```

### **cURL (Shell)**

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"

# Health check
curl -s "$BASE_URL/health" | jq

# Top repos
curl -s "$BASE_URL/api/v1/repos/top10?limit=5" | jq '.repositories[] | "\(.rank). \(.repo_full_name)"'

# RAG query
curl -s -X POST "$BASE_URL/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "Which repos are most active?"}' \
  | jq -r '.answer'
```

---

## 🔗 Additional Resources

- **OpenAPI Documentation:** `http://localhost:8000/docs` (Swagger UI)
- **ReDoc Documentation:** `http://localhost:8000/redoc`
- **WebSocket Guide:** See `WEBSOCKET_GUIDE.md`
- **GitHub Repository:** [Your repo URL]

---

## 📞 Support

For issues or questions:
- Open an issue on GitHub
- Contact: your-email@example.com

---

**Last Updated:** January 15, 2026  
**API Version:** 1.0.0

