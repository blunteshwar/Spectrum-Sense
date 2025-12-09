# Spectrum Sense - RAG Chatbot for Spectrum Web Components

A RAG (Retrieval-Augmented Generation) chatbot that answers questions about Spectrum Web Components by indexing:
- **Documentation pages** from the SWC docs site
- **Source code** from the GitHub repository
- **Slack conversations** (optional)

Built with FastAPI, Qdrant, Ollama, and Spectrum Web Components.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Ingesting Real Data](#ingesting-real-data)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

---

## How It Works

### Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Data Sources   │ ──▶ │   Ingestion     │ ──▶ │   Vector DB     │
│                 │     │   Pipeline      │     │   (Qdrant)      │
│ • SWC Docs URLs │     │                 │     │                 │
│ • GitHub Repo   │     │ 1. Crawl/Clone  │     │ Embeddings +    │
│ • Slack Export  │     │ 2. Chunk text   │     │ Metadata        │
└─────────────────┘     │ 3. Embed        │     └────────┬────────┘
                        │ 4. Index        │              │
                        └─────────────────┘              │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     User        │ ◀── │   LLM (Ollama)  │ ◀── │   Retriever     │
│                 │     │                 │     │                 │
│ Asks question   │     │ Generates       │     │ Semantic search │
│ Gets answer +   │     │ answer from     │     │ + BM25 rerank   │
│ sources         │     │ context         │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### How Documentation is Indexed

The **SWC Docs Crawler** (`ingest/swc_docs_crawler.py`):
1. Reads a list of URLs from a text file (e.g., `sample_data/swc_urls.txt`)
2. Fetches each page via HTTP
3. Extracts content using BeautifulSoup (title, headings, body text, code blocks)
4. Saves to JSONL format

### How GitHub Code is Indexed

The **GitHub Ingester** (`ingest/github_ingester.py`):
1. Clones the repository using `git clone --depth 1`
2. Walks through all files matching specified extensions (`.ts`, `.js`, `.md`, `.css`)
3. Skips `node_modules`, `dist`, `build`, etc.
4. Extracts file content with metadata (path, title, code structure)
5. Saves to JSONL format

### Chunking & Embedding

All data sources go through:
1. **Normalization**: Clean whitespace, extract code blocks
2. **Chunking**: Split into ~1000 char chunks with 200 char overlap
3. **Embedding**: Convert to vectors using `sentence-transformers/all-mpnet-base-v2`
4. **Indexing**: Store in Qdrant vector database

---

## Prerequisites

- **Docker** and **Docker Compose**
- ~10GB disk space (for models and data)
- 8GB+ RAM recommended

---

## Quick Start

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd Spectrum-Sense
```

### Step 2: Start All Services

```bash
cd deploy
docker compose up -d
```

This starts:
| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Chat interface |
| API | 8000 | FastAPI backend |
| Qdrant | 6333 | Vector database |
| Ollama | 11434 | LLM service |

Wait ~60 seconds for services to initialize.

### Step 3: Download the LLM Model

```bash
docker exec spectrum-ollama ollama pull mistral:7b
```

This downloads Mistral 7B (~4GB). Other options: `llama2:7b`, `codellama:7b`.

### Step 4: Verify Services

```bash
# Check all services are healthy
docker compose ps

# Test API health
curl http://localhost:8000/health
```

### Step 5: Open the Chat Interface

Navigate to **http://localhost:3000** in your browser.

---

## Ingesting Real Data

### Option A: Ingest via API (Recommended)

#### 1. Prepare Your URLs File

Edit `sample_data/swc_urls.txt` with documentation URLs (one per line):

```
https://opensource.adobe.com/spectrum-web-components
https://opensource.adobe.com/spectrum-web-components/components/button
https://opensource.adobe.com/spectrum-web-components/components/popover
# ... more URLs
```

#### 2. Trigger Ingestion

**Ingest SWC Documentation only:**
```bash
curl -X POST http://localhost:8000/ingest/run \
  -H "Content-Type: application/json" \
  -d '{
    "source": "swc_docs",
    "urls_file": "/app/sample_data/swc_urls.txt"
  }'
```

**Ingest GitHub Repository only:**
```bash
curl -X POST http://localhost:8000/ingest/run \
  -H "Content-Type: application/json" \
  -d '{
    "source": "github",
    "github_repo": "https://github.com/adobe/spectrum-web-components",
    "github_branch": "main"
  }'
```

**Ingest Both (Recommended):**
```bash
curl -X POST http://localhost:8000/ingest/run \
  -H "Content-Type: application/json" \
  -d '{
    "source": "all",
    "urls_file": "/app/sample_data/swc_urls.txt",
    "github_repo": "https://github.com/adobe/spectrum-web-components"
  }'
```

### Option B: Ingest via CLI (Local Development)

#### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 2. Start Qdrant

```bash
cd deploy
docker compose up -d qdrant
```

#### 3. Crawl Documentation

```bash
python -m ingest.swc_docs_crawler sample_data/swc_urls.txt \
  --output data/swc_docs_raw.jsonl
```

#### 4. Clone and Ingest GitHub Repository

```bash
python -m ingest.github_ingester https://github.com/adobe/spectrum-web-components \
  --output data/github_raw.jsonl \
  --branch main \
  --extensions .ts .js .md .css
```

#### 5. Chunk the Data

```bash
# Chunk docs
python -m ingest.normalize_and_chunk data/swc_docs_raw.jsonl \
  --output data/chunks/swc_docs_chunks.jsonl \
  --source swc_docs

# Chunk code
python -m ingest.normalize_and_chunk data/github_raw.jsonl \
  --output data/chunks/github_chunks.jsonl \
  --source github
```

#### 6. Compute Embeddings and Index

```bash
# Index docs
python -m embeddings.compute_embeddings data/chunks/swc_docs_chunks.jsonl

# Index code
python -m embeddings.compute_embeddings data/chunks/github_chunks.jsonl
```

### Adding Slack Data (Optional)

1. Export your Slack workspace (JSON format)
2. Set the environment variable or use CLI:

```bash
# Via API
export SLACK_EXPORT_PATH=/path/to/slack/export
curl -X POST http://localhost:8000/ingest/run \
  -H "Content-Type: application/json" \
  -d '{"source": "slack"}'

# Via CLI
python -m ingest.slack_importer /path/to/slack/export \
  --output data/slack_raw.jsonl
```

---

## Architecture

### Project Structure

```
Spectrum-Sense/
├── api/                    # FastAPI application
│   └── app.py             # Main API endpoints
├── ingest/                 # Data ingestion pipeline
│   ├── swc_docs_crawler.py    # Crawl docs from URL list
│   ├── github_ingester.py     # Clone and index GitHub repos
│   ├── slack_importer.py      # Import Slack exports
│   ├── spectrum_crawler.py    # Legacy crawler (auto-discovery)
│   └── normalize_and_chunk.py # Text chunking
├── embeddings/             # Embedding computation
│   └── compute_embeddings.py
├── vector/                 # Vector database client
│   └── qdrant_client.py
├── retriever/              # Search and retrieval
│   └── service.py         # Semantic search + BM25 reranking
├── llm_service/            # LLM integration
│   └── serve.py           # Ollama client
├── frontend/               # Chat UI (Spectrum Web Components)
├── deploy/                 # Docker Compose configuration
├── sample_data/            # Sample data and URL lists
│   └── swc_urls.txt       # Documentation URLs to crawl
├── data/                   # Generated data (gitignored)
│   └── chunks/            # Chunked documents
├── repos/                  # Cloned repositories (gitignored)
└── tests/                  # Test suite
```

### Data Sources

| Source | Ingester | Input | Output |
|--------|----------|-------|--------|
| SWC Docs | `swc_docs_crawler.py` | URL list file | `swc_docs_raw.jsonl` |
| GitHub | `github_ingester.py` | Repo URL | `github_raw.jsonl` |
| Slack | `slack_importer.py` | Export directory | `slack_raw.jsonl` |

---

## API Reference

### POST /answer

Query the RAG system.

```bash
curl -X POST http://localhost:8000/answer \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I use sp-popover?",
    "top_k": 5
  }'
```

**Response:**
```json
{
  "answer": "To use sp-popover, you need to...",
  "sources": [
    {
      "title": "Popover",
      "heading_path": "Components > Popover",
      "url": "https://opensource.adobe.com/spectrum-web-components/components/popover",
      "snippet": "The sp-popover component...",
      "chunk_id": "abc123"
    }
  ],
  "used_snippet_ids": ["abc123"],
  "meta": {"latency_ms": 312}
}
```

### POST /ingest/run

Trigger data ingestion.

```bash
curl -X POST http://localhost:8000/ingest/run \
  -H "Content-Type: application/json" \
  -d '{
    "source": "swc_docs|github|slack|all",
    "urls_file": "/app/sample_data/swc_urls.txt",
    "github_repo": "https://github.com/adobe/spectrum-web-components",
    "github_branch": "main"
  }'
```

### GET /health

Health check endpoint.

```bash
curl http://localhost:8000/health
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_HOST` | `localhost` | Qdrant hostname |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `QDRANT_COLLECTION_NAME` | `spectrum_docs` | Collection name |
| `LLM_SERVICE_URL` | `http://ollama:11434` | Ollama URL |
| `LLM_MODEL` | `mistral:7b` | LLM model name |
| `EMBEDDING_MODEL` | `sentence-transformers/all-mpnet-base-v2` | Embedding model |
| `RETRIEVER_TOP_K` | `50` | Initial retrieval count |
| `USE_BM25_RERANKER` | `true` | Enable BM25 reranking |
| `SWC_DOCS_URLS_FILE` | - | Path to URLs file |
| `GITHUB_REPO_URL` | `https://github.com/adobe/spectrum-web-components` | Default repo |
| `GITHUB_BRANCH` | `main` | Default branch |
| `GITHUB_CLONE_DIR` | `./repos` | Where to clone repos |
| `SLACK_EXPORT_PATH` | - | Slack export path |

### Changing the LLM Model

```bash
# Pull a different model
docker exec spectrum-ollama ollama pull llama2:7b

# Update docker-compose.yml
# environment:
#   - LLM_MODEL=llama2:7b

# Restart API
docker compose restart api
```

---

## Development

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

Dev server runs at http://localhost:3000 with hot reload.

### Running Tests

```bash
# All tests
pytest tests/ -v

# E2E tests (requires services running)
pytest tests/test_e2e.py -v

# Health integration tests
pytest tests/test_health_integration.py -v
```

### PR Validation

```bash
./scripts/validate_pr.sh
```

---

## Troubleshooting

### Services Not Starting

```bash
# Check logs
docker compose logs

# Check specific service
docker logs spectrum-api
```

### API Health Check Failing

```bash
# Verify Qdrant
curl http://localhost:6333/health

# Verify Ollama
curl http://localhost:11434/api/tags

# Check if model is downloaded
docker exec spectrum-ollama ollama list
```

### Ingestion Errors

```bash
# Check API logs during ingestion
docker logs -f spectrum-api

# Verify URLs file exists
cat sample_data/swc_urls.txt
```

### Reset Everything

```bash
cd deploy
docker compose down -v
docker compose up -d
```

### Out of Memory

- Reduce `RETRIEVER_TOP_K` value
- Use a smaller LLM model (e.g., `mistral:7b` instead of `llama2:13b`)
- Increase Docker memory allocation

---

## License

Internal use only.
