# Quick Start Guide

## Prerequisites

- Docker and Docker Compose installed

## Step 1: Start Services

```bash
cd deploy
docker compose up -d
```

This starts:
- **Qdrant** (vector database) on `http://localhost:6333`
- **Ollama** (LLM service) on `http://localhost:11434`
- **API Server** on `http://localhost:8000`
- **Frontend** on `http://localhost:3000` ⬅️ **Open this in your browser!**

Wait for all services to be healthy (about 60 seconds for first build).

### Download LLM Model

Before using the API, download the Mistral 7B model:

```bash
docker exec spectrum-ollama ollama pull mistral:7b
```

This downloads approximately 4GB and may take a few minutes depending on your internet connection.

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

## Step 3: Open the Frontend

Navigate to **http://localhost:3000** in your browser.

You'll see the SpectrumGPT chat interface. Try asking questions about Spectrum components!

### Example Questions
- "How do I use sp-popover with pointerdown?"
- "What button variants are available?"
- "How do I create an accessible dialog?"

## Step 4: Test the API (Optional)

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
- See `frontend/README.md` for frontend customization
- See `design_notes.md` for architecture details
- Run tests: `pytest tests/ -v`

## Frontend Development

For frontend development with hot reload:

```bash
cd frontend
npm install
npm run dev
```

The dev server runs at http://localhost:3000 and proxies API requests to the backend.

