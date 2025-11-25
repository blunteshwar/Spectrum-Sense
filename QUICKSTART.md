# Quick Start Guide

## Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ (for local development without Docker)

## Step 1: Start Services

```bash
cd deploy
docker compose up -d
```

This starts:
- **Qdrant** (vector database) on `http://localhost:6333`
- **LLM Mock Server** on `http://localhost:8001`
- **API Server** on `http://localhost:8000`

Wait for all services to be healthy (about 30 seconds).

## Step 2: Index Sample Data

```bash
cd ..
./scripts/reset_local_db.sh
```

This will:
1. Process sample Spectrum HTML pages
2. Process sample Slack export
3. Chunk the content
4. Compute embeddings
5. Index into Qdrant

## Step 3: Test the API

### Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "components": {
    "qdrant": "healthy (points: X)",
    "llm": "healthy",
    "retriever": "healthy"
  }
}
```

### Query Example

```bash
curl -X POST http://localhost:8000/answer \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I use sp-popover with pointerdown?",
    "top_k": 5
  }'
```

Expected response:
```json
{
  "answer": "Based on the retrieved documentation...",
  "sources": [
    {
      "title": "sp-popover Component",
      "heading_path": "Components > Popover > Usage",
      "url": "https://spectrum.adobe.com/components/popover",
      "snippet": "When opening a popover on pointerdown...",
      "chunk_id": "..."
    }
  ],
  "used_snippet_ids": ["..."],
  "meta": {
    "latency_ms": 312
  }
}
```

### Trigger Ingestion

```bash
curl -X POST http://localhost:8000/ingest/run \
  -H "Content-Type: application/json" \
  -d '{"source": "all"}'
```

## Troubleshooting

### Services Not Starting

Check logs:
```bash
cd deploy
docker compose logs
```

### Qdrant Not Accessible

Verify Qdrant is running:
```bash
curl http://localhost:6333/health
```

### API Errors

Check API logs:
```bash
docker logs spectrum-api
```

### Reset Everything

```bash
cd deploy
docker compose down -v
docker compose up -d
cd ..
./scripts/reset_local_db.sh
```

## Next Steps

- See `README.md` for full documentation
- See `design_notes.md` for architecture details
- Run tests: `pytest tests/ -v`

