# Spectrum RAG Backend

Backend for an internal RAG chatbot that answers questions about Adobe Spectrum and Spectrum Web Components (SWC).

## Features

- **Ingest Pipeline**: Crawl Spectrum docs and import Slack exports with PII redaction
- **Embeddings**: Compute embeddings using sentence-transformers
- **Vector DB**: Index and search using Qdrant
- **Retriever**: Semantic search with optional BM25 re-ranking
- **LLM Service**: Configurable LLM inference (mock for local dev, real models for production)
- **REST API**: FastAPI endpoints for querying and ingestion

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- (Optional) GPU for running real LLM models

### Local Development with Docker Compose

1. **Start services**:
   ```bash
   cd deploy
   docker compose up -d
   ```

   This starts:
   - Qdrant (vector DB) on port 6333
   - LLM mock server on port 8001
   - API server on port 8000

2. **Index sample data**:
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

### Local Development (Without Docker)

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Qdrant** (using Docker):
   ```bash
   docker run -d -p 6333:6333 qdrant/qdrant
   ```

3. **Set environment variables**:
   ```bash
   export QDRANT_HOST=localhost
   export QDRANT_PORT=6333
   export USE_MOCK_LLM=true
   ```

4. **Run the API**:
   ```bash
   uvicorn api.app:app --reload --port 8000
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
- `LLM_SERVICE_URL`: LLM service URL (default: http://llm-mock:8001)
- `USE_MOCK_LLM`: Use mock LLM (default: true)
- `EMBEDDING_MODEL`: Embedding model (default: sentence-transformers/all-mpnet-base-v2)
- `RETRIEVER_TOP_K`: Initial retrieval count (default: 50)
- `USE_BM25_RERANKER`: Enable BM25 re-ranking (default: true)

## Switching LLM Backends

### Option A: GPU-based (text-generation-inference)

1. **Start TGI server** (requires GPU):
   ```bash
   docker run --gpus all -p 8001:80 \
     -v /path/to/models:/models \
     ghcr.io/huggingface/text-generation-inference:latest \
     --model-id mistralai/Mistral-7B-Instruct-v0.2
   ```

2. **Update docker-compose.yml**:
   ```yaml
   llm-service:
     image: ghcr.io/huggingface/text-generation-inference:latest
     # ... configuration
   ```

3. **Set environment**:
   ```bash
   export LLM_SERVICE_URL=http://localhost:8001
   export USE_MOCK_LLM=false
   ```

### Option B: CPU-based (llama.cpp)

1. **Download model** (e.g., Mistral 7B quantized):
   ```bash
   wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf
   ```

2. **Start llama.cpp server**:
   ```bash
   ./llama-server -m mistral-7b-instruct-v0.2.Q4_K_M.gguf -p 8001
   ```

3. **Update API to use llama.cpp API format** (modify `llm_service/serve.py`)

## Adding Slack Export

1. **Export Slack data**:
   - Go to Slack workspace settings
   - Request export (JSON format)
   - Download and extract

2. **Import**:
   ```bash
   python ingest/slack_importer.py /path/to/slack/export --output data/slack_raw.jsonl
   ```

3. **Chunk and index**:
   ```bash
   python ingest/normalize_and_chunk.py data/slack_raw.jsonl --source slack
   python embeddings/compute_embeddings.py data/chunks/slack_chunks.jsonl
   ```

## Testing

Run tests:
```bash
pytest tests/
```

Run E2E smoke test (requires Qdrant running):
```bash
pytest tests/test_e2e.py -v
```

## Manual Steps Required

### Model Downloads

- **Embedding model**: Automatically downloaded on first use (sentence-transformers)
- **LLM models**: Manual download required for production:
  - GPU: Download from HuggingFace (Mistral-7B-Instruct, Llama-2-13B, etc.)
  - CPU: Download quantized GGUF models for llama.cpp

### GPU Setup

For GPU-based LLM inference:
1. Install NVIDIA drivers
2. Install CUDA toolkit
3. Use `nvidia-docker` or Docker with GPU support
4. See "Switching LLM Backends" above

## Troubleshooting

### Qdrant Connection Error

Ensure Qdrant is running:
```bash
docker ps | grep qdrant
curl http://localhost:6333/health
```

### LLM Service Not Responding

Check mock LLM server:
```bash
curl http://localhost:8001/health
```

For real LLM, check logs and ensure model is loaded.

### Embedding Model Download

First run will download the model (~420MB). Ensure internet connection.

## License

Internal use only.

