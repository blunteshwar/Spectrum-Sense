# Spectrum Sense - RAG Chatbot for Spectrum Web Components

A RAG (Retrieval-Augmented Generation) chatbot that answers questions about Spectrum Web Components by indexing:
- **Documentation pages** from the SWC docs site
- **Source code** from the GitHub repository
- **Slack conversations** (optional)

Built with FastAPI, Qdrant, Ollama, and Spectrum Web Components.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
  - [Step 1: Clone This Repository](#step-1-clone-this-repository)
  - [Step 2: Add Your Documentation URLs](#step-2-add-your-documentation-urls)
  - [Step 3: Start All Services](#step-3-start-all-services)
  - [Step 4: Download the LLM Model](#step-4-download-the-llm-model)
  - [Step 5: Ingest Data](#step-5-ingest-data)
  - [Step 6: Verify and Use](#step-6-verify-and-use)
- [How It Works](#how-it-works)
- [Data Ingestion](#data-ingestion)
  - [Ingesting All Sources](#ingesting-all-sources)
  - [Ingesting Individual Sources](#ingesting-individual-sources)
  - [Controlling Ingestion](#controlling-ingestion)
  - [Ingesting via CLI](#ingesting-via-cli)
- [Rebuilding After Code Changes](#rebuilding-after-code-changes)
- [Resetting Ingested Data](#resetting-ingested-data)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Docker** and **Docker Compose**
- ~10GB disk space (for models and data)
- 8GB+ RAM recommended

---

## Quick Start

### Step 1: Clone This Repository

```bash
git clone <your-repo-url>
cd Spectrum-Sense
```

### Step 2: Add Your Documentation URLs

Edit `sample_data/swc_urls.txt` with the documentation pages you want to index (one URL per line):

```
https://opensource.adobe.com/spectrum-web-components
https://opensource.adobe.com/spectrum-web-components/getting-started
https://opensource.adobe.com/spectrum-web-components/components/button
https://opensource.adobe.com/spectrum-web-components/components/popover
# ... add all your URLs
```

> **Note:** The file already contains ~120 URLs for SWC documentation. You can use it as-is or modify it.

### Step 3: Start All Services

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

### Step 4: Download the LLM Model

   ```bash
   docker exec spectrum-ollama ollama pull mistral:7b
   ```
   
This downloads Mistral 7B (~4GB). Other options: `llama2:7b`, `codellama:7b`.

### Step 5: Ingest Data

Run this command to ingest both the documentation site AND the GitHub codebase (with real-time streaming logs):

   ```bash
curl -N -X POST http://localhost:8000/ingest/run/stream \
  -H "Content-Type: application/json" \
  -d '{
    "source": "all",
    "urls_file": "/app/sample_data/swc_urls.txt",
    "github_repo": "https://github.com/adobe/spectrum-web-components"
  }'
```

> 💡 The `-N` flag disables buffering so you see logs as they stream in real-time.

**Streaming log output example:**
```json
data: {"timestamp": "2025-12-11T10:30:00", "level": "info", "message": "Starting ingestion pipeline", "task_id": "ingest-2025-12-11-103000"}
data: {"timestamp": "2025-12-11T10:30:01", "level": "info", "message": "Crawling [1/5]: https://opensource.adobe.com/..."}
data: {"timestamp": "2025-12-11T10:30:15", "level": "success", "message": "SWC docs chunks indexed successfully"}
```

**What happens automatically:**
1. **Documentation**: Fetches all pages from `swc_urls.txt`, extracts content
2. **GitHub**: **Clones the repo automatically** (you don't need to clone it manually), indexes `.ts`, `.js`, `.md`, `.css` files
3. **Processing**: Chunks text, computes embeddings, indexes into Qdrant

> ⏱️ This may take 45-85 minutes depending on the number of URLs and repo size.

Press `Ctrl+C` to stop watching logs (ingestion continues in background).

### Step 6: Verify and Use

   ```bash
# Check health (should show points count > 0)
   curl http://localhost:8000/health
```

Open **http://localhost:3000** in your browser and start asking questions!

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

The **GitHub Ingester** (`ingest/github_ingester.py`) **automatically clones the repository** - you don't need to clone it manually:

1. **Clones automatically** using `git clone --depth 1` (shallow clone, only latest commit)
2. If already cloned, pulls latest changes
3. Walks through all files matching specified extensions (`.ts`, `.js`, `.md`, `.css`)
4. **Skips directories**: `node_modules`, `dist`, `build`, `test`, `tests`, `stories`, `.git`, etc.
5. **Skips files**: test files (`.test.ts`, `.spec.js`), stories (`.stories.ts`), declaration files (`.d.ts`)
6. Extracts file content with metadata (path, title, code structure)
7. Saves to JSONL format

The cloned repo is stored in the `repos/` directory (gitignored).

### Chunking & Embedding

All data sources go through:
1. **Normalization**: Clean whitespace, extract code blocks
2. **Chunking**: Split into ~1000 char chunks with 200 char overlap
3. **Embedding**: Convert to vectors using `sentence-transformers/all-mpnet-base-v2`
4. **Indexing**: Store in Qdrant vector database

---

## Data Ingestion

### Ingesting All Sources

Ingest documentation, GitHub code, and Slack (if configured) with streaming logs:

```bash
curl -N -X POST http://localhost:8000/ingest/run/stream \
     -H "Content-Type: application/json" \
     -d '{
    "source": "all",
    "urls_file": "/app/sample_data/swc_urls.txt",
    "github_repo": "https://github.com/adobe/spectrum-web-components"
     }'
```

**Alternative: Non-streaming endpoint**

If you prefer a simple response without streaming logs:
```bash
   curl -X POST http://localhost:8000/ingest/run \
     -H "Content-Type: application/json" \
  -d '{"source": "all", "urls_file": "/app/sample_data/swc_urls.txt", "github_repo": "https://github.com/adobe/spectrum-web-components"}'
```

Then watch progress via Docker logs:
```bash
docker logs -f spectrum-api
```

### Ingesting Individual Sources

#### Documentation Only

```bash
curl -N -X POST http://localhost:8000/ingest/run/stream \
  -H "Content-Type: application/json" \
  -d '{
    "source": "swc_docs",
    "urls_file": "/app/sample_data/swc_urls.txt"
  }'
```

#### GitHub Repository Only

The script **automatically clones** the repository - you don't need to clone it manually.

```bash
curl -N -X POST http://localhost:8000/ingest/run/stream \
  -H "Content-Type: application/json" \
  -d '{
    "source": "github",
    "github_repo": "https://github.com/adobe/spectrum-web-components",
    "github_branch": "main"
  }'
```

**What the script does:**
1. Clones the repo to `repos/spectrum-web-components/` (shallow clone, latest commit only)
2. If already cloned, pulls latest changes
3. Walks all `.ts`, `.js`, `.md`, `.css` files (skips `node_modules`, `dist`, test files, etc.)
4. Extracts content and indexes it

#### Slack Data (Optional)

1. Export your Slack workspace (JSON format)
2. Set the environment variable or use CLI:

```bash
# Via API
export SLACK_EXPORT_PATH=/path/to/slack/export
curl -N -X POST http://localhost:8000/ingest/run/stream \
  -H "Content-Type: application/json" \
  -d '{"source": "slack"}'

# Via CLI
python -m ingest.slack_importer /path/to/slack/export \
  --output data/slack_raw.jsonl
```

### Controlling Ingestion

#### Check Ingestion Status

```bash
curl http://localhost:8000/ingest/status
```

**Response:**
```json
{
  "is_running": true,
  "task_id": "ingest-2025-12-11-103000",
  "started_at": "2025-12-11T10:30:00.123456",
  "cancel_requested": false
}
```

#### Cancel Running Ingestion

To stop an in-progress ingestion:

```bash
curl -X POST http://localhost:8000/ingest/cancel
```

**Response:**
```json
{
  "status": "cancelled",
  "message": "Cancellation requested. The ingestion will stop after the current operation completes.",
  "task_id": "ingest-2025-12-11-103000"
}
```

> **Note:** The ingestion will stop gracefully after the current URL or file is processed. Already indexed data is preserved.

#### Alternative: Force Stop (Restart Container)

If you need to stop immediately without waiting:

```bash
docker restart spectrum-api
```

### Ingesting via CLI (Local Development)

If you prefer running ingestion locally instead of via the API:

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

#### 4. Ingest GitHub Repository

**The script clones the repo automatically** - you don't need to clone it yourself:

```bash
python -m ingest.github_ingester https://github.com/adobe/spectrum-web-components \
  --output data/github_raw.jsonl \
  --branch main \
  --extensions .ts .js .md .css
```

This will:
- Clone to `repos/spectrum-web-components/` (or pull if already exists)
- Index all matching files

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

---

## Rebuilding After Code Changes

If you modify the ingestion code, URL list, or any Python files, you need to rebuild and restart the API container:

### When to Rebuild

Rebuild is required when you change:
- Any Python file (`api/`, `ingest/`, `embeddings/`, etc.)
- `requirements.txt` or `requirements-prod.txt`
- `Dockerfile`

Rebuild is **NOT** required when you only change:
- `sample_data/swc_urls.txt` (just re-run ingestion)
- `docker-compose.yml` (just restart)

### How to Rebuild

```bash
cd deploy

# Rebuild the API container
docker compose build api

# Restart with new image
docker compose up -d api

# Wait for it to be healthy (~45 seconds)
docker compose ps api
```

### Force Full Rebuild (if caching issues)

```bash
docker compose build api --no-cache
docker compose up -d api
```

### Watch Logs After Restart

```bash
docker logs -f spectrum-api
```

---

## Resetting Ingested Data

If you want to clear all indexed data and start fresh:

### Option 1: Delete Collection via API (Quick)

```bash
# Delete the Qdrant collection
curl -X DELETE http://localhost:6333/collections/spectrum_docs

# Restart API (recreates empty collection)
cd deploy
docker compose restart api

# Wait for healthy
sleep 45 && curl http://localhost:8000/health
```

### Option 2: Full Volume Reset (Complete Wipe)

```bash
cd deploy

# Stop all services
docker compose down

# Remove Qdrant data volume
docker volume rm deploy_qdrant_data

# Start fresh
docker compose up -d

# Wait for services
sleep 60 && docker compose ps
```

### After Reset: Re-ingest Data

```bash
curl -N -X POST http://localhost:8000/ingest/run/stream \
  -H "Content-Type: application/json" \
  -d '{
    "source": "all",
    "urls_file": "/app/sample_data/swc_urls.txt",
    "github_repo": "https://github.com/adobe/spectrum-web-components"
  }'
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

Trigger data ingestion (non-streaming).

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

### POST /ingest/run/stream

Trigger data ingestion with streaming logs (SSE).

```bash
curl -N -X POST http://localhost:8000/ingest/run/stream \
  -H "Content-Type: application/json" \
  -d '{
    "source": "all",
    "urls_file": "/app/sample_data/swc_urls.txt",
    "github_repo": "https://github.com/adobe/spectrum-web-components"
  }'
```

### GET /ingest/status

Get current ingestion status.

```bash
curl http://localhost:8000/ingest/status
```

**Response:**
```json
{
  "is_running": true,
  "task_id": "ingest-2025-12-11-103000",
  "started_at": "2025-12-11T10:30:00.123456",
  "cancel_requested": false
}
```

### POST /ingest/cancel

Cancel a running ingestion.

```bash
curl -X POST http://localhost:8000/ingest/cancel
```

**Response:**
```json
{
  "status": "cancelled",
  "message": "Cancellation requested. The ingestion will stop after the current operation completes.",
  "task_id": "ingest-2025-12-11-103000"
}
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

# Check ingestion status
curl http://localhost:8000/ingest/status

# Verify URLs file exists
cat sample_data/swc_urls.txt
```

### Ingestion Running Too Long

```bash
# Check status
curl http://localhost:8000/ingest/status

# Cancel gracefully
curl -X POST http://localhost:8000/ingest/cancel

# Or force stop
docker restart spectrum-api
```

### Reset Qdrant Only (Keep LLM Models)

Deletes indexed data but preserves downloaded LLM models:

```bash
cd deploy
docker compose down
docker volume rm deploy_qdrant_data
docker compose up -d
```

Then re-ingest your data.

### Full Reset (Delete Everything)

Deletes ALL data including:
- Qdrant indexed vectors (requires re-ingestion)
- Ollama models (requires re-downloading ~4GB)

```bash
cd deploy
docker compose down -v
docker compose up -d

# Re-download LLM model
docker exec spectrum-ollama ollama pull mistral:7b
```

### Out of Memory

- Reduce `RETRIEVER_TOP_K` value
- Use a smaller LLM model (e.g., `mistral:7b` instead of `llama2:13b`)
- Increase Docker memory allocation

---

## License

Internal use only.
