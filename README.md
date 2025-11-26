# Spectrum RAG Backend

Backend for an internal RAG chatbot that answers questions about Adobe Spectrum and Spectrum Web Components (SWC).

## Features

- **Ingest Pipeline**: Crawl Spectrum docs and import Slack exports with PII redaction
- **Embeddings**: Compute embeddings using sentence-transformers
- **Vector DB**: Index and search using Qdrant
- **Retriever**: Semantic search with optional BM25 re-ranking
- **LLM Service**: LLM inference using Ollama (runs locally)
- **REST API**: FastAPI endpoints for querying and ingestion

## Quick Start

### Prerequisites

- Docker and Docker Compose

### Local Development with Docker Compose

1. **Start services**:
   ```bash
   cd deploy
   docker compose up -d
   ```

   This starts:
   - Qdrant (vector DB) on port 6333
   - Ollama (LLM service) on port 11434
   - API server on port 8000

2. **Download the LLM model** (first time only):
   ```bash
   docker exec spectrum-ollama ollama pull mistral:7b
   ```
   
   This downloads the Mistral 7B model (~4GB). You can use other models like `llama2:7b`, `codellama:7b`, etc.

3. **Index sample data**:
   ```bash
   ./scripts/reset_local_db.sh
   ```

3. **Test the API**:
   ```bash
   # Health check
   curl http://localhost:8000/health

   # Query
   curl -X POST http://localhost:8000/answer \
     -H "Content-Type: application/json" \
     -d '{
       "query": "How do I use sp-popover with pointerdown?",
       "top_k": 5
     }'

   # Trigger ingestion
   curl -X POST http://localhost:8000/ingest/run \
     -H "Content-Type: application/json" \
     -d '{"source": "all"}'
   ```

## Project Structure

```
.
├── api/                 # FastAPI application
│   └── app.py          # Main API endpoints
├── ingest/             # Ingestion pipeline
│   ├── spectrum_crawler.py
│   ├── slack_importer.py
│   └── normalize_and_chunk.py
├── embeddings/         # Embedding computation
│   └── compute_embeddings.py
├── vector/             # Vector DB client
│   └── qdrant_client.py
├── retriever/          # Retrieval service
│   └── service.py
├── llm_service/        # LLM inference
│   └── serve.py
├── tests/              # Test suite
├── deploy/             # Docker Compose configs
├── sample_data/        # Sample data for testing
└── scripts/            # Utility scripts
```

## API Endpoints

### POST /answer

Answer a query using RAG.

**Request**:
```json
{
  "query": "How do I use sp-popover with pointerdown?",
  "conversation_id": "optional-string",
  "top_k": 5
}
```

**Response**:
```json
{
  "answer": "Short answer...",
  "sources": [
    {
      "title": "sp-popover",
      "heading_path": "Components > Popover > Usage",
      "url": "https://spectrum.adobe.com/...",
      "snippet": "When opening a popover on pointerdown...",
      "chunk_id": "abc123"
    }
  ],
  "used_snippet_ids": ["abc123"],
  "meta": {"latency_ms": 312}
}
```

### POST /ingest/run

Trigger ingestion pipeline.

**Request**:
```json
{
  "source": "spectrum|slack|all"
}
```

**Response**:
```json
{
  "status": "started",
  "task_id": "ingest-2025-11-25-1"
}
```

### GET /health

Health check endpoint.

## Configuration

Environment variables (see `.env.example`):

- `QDRANT_HOST`: Qdrant host (default: localhost)
- `QDRANT_PORT`: Qdrant port (default: 6333)
- `QDRANT_COLLECTION_NAME`: Collection name (default: spectrum_docs)
- `LLM_SERVICE_URL`: LLM service URL (default: http://ollama:11434)
- `LLM_MODEL`: Ollama model name (default: mistral:7b)
- `EMBEDDING_MODEL`: Embedding model (default: sentence-transformers/all-mpnet-base-v2)
- `RETRIEVER_TOP_K`: Initial retrieval count (default: 50)
- `USE_BM25_RERANKER`: Enable BM25 re-ranking (default: true)
- `SLACK_EXPORT_PATH`: Path to your Slack export JSON file or directory (default: `sample_data/slack_sample.json`)

## Switching LLM Models

Ollama supports many models. To use a different model:

1. **Pull a different model**:
   ```bash
   docker exec spectrum-ollama ollama pull llama2:7b
   # or
   docker exec spectrum-ollama ollama pull codellama:7b
   # or
   docker exec spectrum-ollama ollama pull mistral:7b-instruct
   ```

2. **Update the model name** in `docker-compose.yml`:
   ```yaml
   environment:
     - LLM_MODEL=llama2:7b
   ```

3. **Restart the API service**:
   ```bash
   docker compose restart api
   ```

## Adding Slack Export

1. **Export Slack data**:
   - Go to Slack workspace settings
   - Request export (JSON format)
   - Download and extract

2. **Configure the export path** (choose one method):

   **Option A: Using environment variable** (recommended for API ingestion):
   ```bash
   export SLACK_EXPORT_PATH=/path/to/your/slack/export
   # Can be a single JSON file or a directory containing channel JSON files
   ```

   **Option B: Using CLI tool**:
   ```bash
   python ingest/slack_importer.py /path/to/slack/export --output data/slack_raw.jsonl
   ```

3. **Ingest via API** (if using Option A):
   ```bash
   curl -X POST http://localhost:8000/ingest/run \
     -H "Content-Type: application/json" \
     -d '{"source": "slack"}'
   ```

   **Or chunk and index manually** (if using Option B):
   ```bash
   python ingest/normalize_and_chunk.py data/slack_raw.jsonl --source slack
   python embeddings/compute_embeddings.py data/chunks/slack_chunks.jsonl
   ```

## Testing

Run all tests:
```bash
pytest tests/
```

Run E2E smoke test (requires Qdrant running):
```bash
pytest tests/test_e2e.py -v
```

### PR Validation

Before merging PRs, run health check and integration tests to verify all services are working:

```bash
# Using the validation script (recommended)
./scripts/validate_pr.sh

# Or using make
make test-health

# Or directly with pytest
pytest tests/test_health_integration.py -v -m "not slow"
```

The validation script checks:
- ✅ All services (Qdrant, Ollama, API) are running and healthy
- ✅ Ollama has the required model downloaded
- ✅ LLM service is not using mock (real Ollama integration)
- ✅ API endpoints return correct structure
- ✅ RAG pipeline works end-to-end

For full integration tests including slow tests:
```bash
pytest tests/test_health_integration.py -v
```

## Manual Steps Required

### Model Downloads

- **Embedding model**: Automatically downloaded on first use (sentence-transformers)
- **LLM models**: Manual download required for production:
  - CPU: Download quantized GGUF models for llama.cpp

## Troubleshooting

### Qdrant Connection Error

Ensure Qdrant is running:
```bash
docker ps | grep qdrant
curl http://localhost:6333/health
```

### LLM Service Not Responding

Check Ollama service:
```bash
curl http://localhost:11434/api/tags
```

Ensure the model is downloaded:
```bash
docker exec spectrum-ollama ollama pull mistral:7b
```

### Embedding Model Download

First run will download the model (~420MB). Ensure internet connection.

## License

Internal use only.

