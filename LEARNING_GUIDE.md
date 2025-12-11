# Spectrum-Sense Learning Guide

A comprehensive Knowledge Transfer (KT) document for junior developers to understand and work with this RAG (Retrieval-Augmented Generation) chatbot project.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Key Concepts You Need to Know](#2-key-concepts-you-need-to-know)
3. [Architecture Deep Dive](#3-architecture-deep-dive)
4. [Project Structure](#4-project-structure)
5. [Component Breakdown](#5-component-breakdown)
6. [Data Flow Explained](#6-data-flow-explained)
7. [Code Walkthrough](#7-code-walkthrough)
8. [Development Workflow](#8-development-workflow)
9. [Common Tasks](#9-common-tasks)
10. [Troubleshooting Guide](#10-troubleshooting-guide)
11. [Glossary](#11-glossary)

---

## 1. Project Overview

### What is Spectrum-Sense?

Spectrum-Sense is an **internal RAG chatbot** that answers questions about Adobe Spectrum Web Components. It:

1. **Ingests** documentation and source code from multiple sources
2. **Indexes** the content in a vector database for semantic search
3. **Retrieves** relevant content when a user asks a question
4. **Generates** human-readable answers using an LLM (Large Language Model)

### Why RAG?

**RAG (Retrieval-Augmented Generation)** solves a key problem with LLMs:

- **Problem**: LLMs have a knowledge cutoff and can hallucinate facts
- **Solution**: RAG retrieves actual documents and gives them to the LLM as context
- **Result**: Answers are grounded in real documentation, with citations

### Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend API | FastAPI (Python) | REST API for queries and ingestion |
| Vector Database | Qdrant | Stores embeddings for semantic search |
| LLM Service | Ollama | Runs LLM locally (Mistral 7B) |
| Embedding Model | sentence-transformers | Converts text to vectors |
| Frontend | Spectrum Web Components | Chat UI |
| Containerization | Docker Compose | Orchestrates all services |

---

## 2. Key Concepts You Need to Know

### 2.1 Embeddings

**What are embeddings?**

Embeddings are numerical representations (vectors) of text. They capture the *meaning* of text, not just the words.

```
"How do I use a button?" → [0.23, -0.45, 0.12, ..., 0.67]  (768 dimensions)
"Using buttons in my app" → [0.21, -0.43, 0.14, ..., 0.65]  (similar vector!)
```

**Why they matter:**
- Similar meanings = similar vectors
- We can find related content by comparing vectors
- This enables "semantic search" (search by meaning, not keywords)

**In this project:**
- We use `sentence-transformers/all-mpnet-base-v2`
- It produces 768-dimensional vectors
- Code location: `embeddings/compute_embeddings.py`

### 2.2 Vector Database (Qdrant)

**What is a vector database?**

A specialized database optimized for storing and searching vectors (embeddings).

**How it works:**
1. Store vectors with metadata (payloads)
2. Search by similarity: "Find vectors closest to this query vector"
3. Uses algorithms like HNSW for fast approximate nearest neighbor search

**Key operations:**
```python
# Upsert (insert/update)
vector_client.upsert_batch(vectors, payloads)

# Search
results = vector_client.search(query_vector, top_k=10)
```

**In this project:**
- Qdrant runs as a Docker container on port 6333
- Collection name: `spectrum_docs`
- Code location: `vector/qdrant_client.py`

### 2.3 Chunking

**What is chunking?**

Breaking large documents into smaller pieces (chunks) for:
1. **Better retrieval**: Match specific sections, not whole documents
2. **Token limits**: LLMs have context limits (e.g., 4096 tokens)
3. **Precision**: Return only relevant parts

**Chunking strategy in this project:**
- Chunk size: ~1000 characters
- Overlap: 200 characters (ensures context isn't lost at boundaries)

```
Document: "Paragraph 1... Paragraph 2... Paragraph 3..."
                    ↓
Chunk 1: "Paragraph 1... [part of Paragraph 2]"
Chunk 2: "[part of Paragraph 2]... Paragraph 3..."
              ↑ overlap ↑
```

**Code location:** `ingest/normalize_and_chunk.py`

### 2.4 BM25 Re-ranking

**What is BM25?**

A traditional keyword-based ranking algorithm (used by search engines like Elasticsearch).

**Why combine vector search + BM25?**

| Vector Search | BM25 |
|--------------|------|
| Good at semantic similarity | Good at exact keyword matches |
| "How to style buttons" matches "button customization" | "sp-button" matches "sp-button" exactly |

**Hybrid approach:**
1. Vector search returns top 50 results
2. BM25 re-ranks them based on keyword matching
3. Final score = 70% vector + 30% BM25

**Code location:** `retriever/service.py`

### 2.5 Prompt Engineering

**What is prompt engineering?**

Designing the instructions given to an LLM to get better outputs.

**Our system prompt (simplified):**
```
You are SpectrumGPT — an expert assistant for Spectrum Web Components.
Guidelines:
1. Use ONLY the retrieved passages for facts
2. Include code examples
3. Structure your answer clearly
4. Cite sources

Retrieved passages:
{context}

User question: {query}
```

**Code location:** `llm_service/serve.py`

---

## 3. Architecture Deep Dive

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Docker Compose                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐            │
│  │   Frontend   │────▶│   API        │────▶│   Qdrant     │            │
│  │   (Nginx)    │     │   (FastAPI)  │     │ (Vector DB)  │            │
│  │   :3000      │     │   :8000      │     │   :6333      │            │
│  └──────────────┘     └──────┬───────┘     └──────────────┘            │
│                              │                                          │
│                              ▼                                          │
│                       ┌──────────────┐                                  │
│                       │   Ollama     │                                  │
│                       │   (LLM)      │                                  │
│                       │   :11434     │                                  │
│                       └──────────────┘                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Request Flow (Query)

```
User asks: "How do I use sp-button?"
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. Frontend sends POST /answer                                          │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. API computes query embedding                                          │
│    "How do I use sp-button?" → [0.23, -0.45, ...]                        │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. Qdrant searches for similar vectors                                   │
│    Returns top 50 chunks with payloads                                   │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. BM25 re-ranks results                                                 │
│    Keyword matching + source boost → top 5 chunks                        │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. LLM generates answer with context                                     │
│    System prompt + chunks + query → Ollama → Answer                      │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. Response returned with answer + sources                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### Ingestion Flow

```
Data Sources                    Processing                     Storage
─────────────                   ──────────                     ───────
                                
SWC Docs URLs ─────┐
(swc_urls.txt)     │
                   │            ┌───────────────┐
                   ├──────────▶ │ 1. Crawl/     │
GitHub Repo  ──────┤            │    Clone      │
(auto-cloned)      │            └───────┬───────┘
                   │                    │
Slack Export ──────┘                    ▼
(optional)                      ┌───────────────┐
                                │ 2. Extract    │────▶ raw.jsonl
                                │    Content    │
                                └───────┬───────┘
                                        │
                                        ▼
                                ┌───────────────┐
                                │ 3. Normalize  │────▶ chunks.jsonl
                                │    & Chunk    │
                                └───────┬───────┘
                                        │
                                        ▼
                                ┌───────────────┐
                                │ 4. Compute    │
                                │   Embeddings  │
                                └───────┬───────┘
                                        │
                                        ▼
                                ┌───────────────┐
                                │ 5. Index in   │────▶ Qdrant
                                │    Qdrant     │
                                └───────────────┘
```

---

## 4. Project Structure

```
Spectrum-Sense/
│
├── api/                          # FastAPI Backend
│   ├── __init__.py
│   └── app.py                    # Main API endpoints
│
├── ingest/                       # Data Ingestion Pipeline
│   ├── __init__.py
│   ├── swc_docs_crawler.py       # Crawls documentation URLs
│   ├── github_ingester.py        # Clones and indexes GitHub repos
│   ├── slack_importer.py         # Imports Slack exports
│   └── normalize_and_chunk.py    # Text normalization and chunking
│
├── embeddings/                   # Embedding Computation
│   ├── __init__.py
│   └── compute_embeddings.py     # Converts text to vectors
│
├── vector/                       # Vector Database Client
│   ├── __init__.py
│   └── qdrant_client.py          # Qdrant operations wrapper
│
├── retriever/                    # Search and Retrieval
│   ├── __init__.py
│   └── service.py                # Vector search + BM25 re-ranking
│
├── llm_service/                  # LLM Integration
│   ├── __init__.py
│   └── serve.py                  # Prompt composition + Ollama client
│
├── frontend/                     # Chat UI
│   ├── src/
│   │   ├── spectrum-chat-app.js  # Main chat application
│   │   ├── chat-message.js       # Message rendering
│   │   └── sources-panel.js      # Sources display
│   ├── index.html
│   ├── Dockerfile
│   └── package.json
│
├── deploy/                       # Deployment Configuration
│   └── docker-compose.yml        # Docker services definition
│
├── sample_data/                  # Sample Data for Testing
│   └── swc_urls.txt              # Documentation URLs to crawl
│
├── tests/                        # Test Suite
│   ├── test_e2e.py               # End-to-end tests
│   ├── test_health_integration.py # Health check tests
│   └── ...
│
├── data/                         # Generated Data (gitignored)
│   ├── swc_docs_raw.jsonl        # Raw crawled content
│   ├── github_raw.jsonl          # Raw GitHub content
│   └── chunks/                   # Chunked content
│       ├── swc_docs_chunks.jsonl
│       └── github_chunks.jsonl
│
├── repos/                        # Cloned Repos (gitignored)
│   └── spectrum-web-components/  # Auto-cloned repo
│
├── Dockerfile                    # API container image
├── requirements.txt              # Python dependencies
├── requirements-prod.txt         # Production dependencies
└── README.md                     # Main documentation
```

---

## 5. Component Breakdown

### 5.1 API (`api/app.py`)

**Purpose:** Main FastAPI application with REST endpoints.

**Key Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Check service health |
| `/answer` | POST | Answer a user query |
| `/ingest/run` | POST | Start ingestion (non-streaming) |
| `/ingest/run/stream` | POST | Start ingestion with streaming logs |
| `/ingest/status` | GET | Check ingestion status |
| `/ingest/cancel` | POST | Cancel running ingestion |

**Key Code Patterns:**

```python
# Startup event - initialize services
@app.on_event("startup")
async def startup_event():
    global vector_client, embedding_computer, retriever_service, llm_service
    
    # Initialize Qdrant client
    vector_client = QdrantClientWrapper(host=qdrant_host, port=qdrant_port)
    
    # Initialize embedding model
    embedding_computer = EmbeddingComputer(model_name=embedding_model)
    
    # Initialize retriever
    retriever_service = RetrieverService(vector_client, embedding_computer)
    
    # Initialize LLM
    llm_service = create_llm_service(service_url=llm_url, model_name=llm_model)
```

### 5.2 Ingestion Pipeline (`ingest/`)

**SWC Docs Crawler (`swc_docs_crawler.py`):**

```python
class SWCDocsCrawler:
    def crawl_url(self, url: str) -> Optional[Dict]:
        # 1. Fetch HTML via HTTP
        response = self.client.get(url)
        
        # 2. Parse with BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        
        # 3. Extract content
        title = soup.find("title").get_text()
        body = main_content.get_text()
        code_blocks = [pre.get_text() for pre in soup.find_all("pre")]
        
        # 4. Return structured data
        return {"title": title, "body": body, "code_blocks": code_blocks, "url": url}
```

**GitHub Ingester (`github_ingester.py`):**

```python
class GitHubIngester:
    def clone_repo(self, repo_url: str, branch: str = "main"):
        # Shallow clone (only latest commit)
        subprocess.run(["git", "clone", "--depth", "1", repo_url, repo_path])
    
    def should_index_file(self, file_path: Path) -> bool:
        # Check extension (.ts, .js, .md, .css)
        # Skip test files, node_modules, etc.
        return file_path.suffix in self.extensions and \
               not any(part in self.skip_dirs for part in file_path.parts)
```

**Chunking (`normalize_and_chunk.py`):**

```python
class Chunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str) -> List[str]:
        # Split into words
        words = text.split()
        chunks = []
        current_chunk = []
        
        for word in words:
            current_chunk.append(word)
            if len(" ".join(current_chunk)) > self.chunk_size:
                chunks.append(" ".join(current_chunk))
                # Keep overlap words for next chunk
                current_chunk = current_chunk[-overlap_words:]
        
        return chunks
```

### 5.3 Embeddings (`embeddings/compute_embeddings.py`)

```python
class EmbeddingComputer:
    def __init__(self, model_name: str = "sentence-transformers/all-mpnet-base-v2"):
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()  # 768
    
    def compute_embedding(self, text: str) -> List[float]:
        # Convert text to 768-dimensional vector
        return self.model.encode(text, convert_to_numpy=True).tolist()
    
    def compute_batch(self, texts: List[str]) -> List[List[float]]:
        # Batch processing for efficiency
        return self.model.encode(texts, batch_size=32).tolist()
```

### 5.4 Vector Client (`vector/qdrant_client.py`)

```python
class QdrantClientWrapper:
    def __init__(self, host: str, port: int, collection_name: str):
        self.client = QdrantClient(host=host, port=port)
        self._ensure_collection()  # Create if not exists
    
    def upsert_batch(self, vectors: List[List[float]], payloads: List[Dict]):
        # Insert vectors with metadata
        points = [PointStruct(id=i, vector=v, payload=p) for i, (v, p) in enumerate(...)]
        self.client.upsert(collection_name=self.collection_name, points=points)
    
    def search(self, query_vector: List[float], top_k: int = 50) -> List[Dict]:
        # Find similar vectors
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True
        )
        return [{"id": p.id, "score": p.score, "payload": p.payload} for p in results.points]
```

### 5.5 Retriever (`retriever/service.py`)

```python
class RetrieverService:
    SOURCE_BOOST = {
        "swc_docs": 1.3,  # Docs get 30% boost
        "github": 1.0,     # Code gets no boost
        "slack": 1.1,      # Slack gets 10% boost
    }
    
    def retrieve(self, query: str, top_k: int = 50) -> List[Dict]:
        # 1. Compute query embedding
        query_vector = self.embedding_computer.compute_embedding(query)
        
        # 2. Vector search
        results = self.vector_client.search(query_vector, top_k)
        
        # 3. Re-rank with BM25 + source boost
        return self._rerank_bm25(query, results)
    
    def _rerank_bm25(self, query: str, results: List[Dict]) -> List[Dict]:
        # Combine vector score + BM25 score + source boost
        for result in results:
            vector_score = result["score"]
            bm25_score = self.bm25_index.get_scores(query.split())[i]
            source_boost = self.SOURCE_BOOST.get(result["payload"]["source"], 1.0)
            
            final_score = (0.7 * vector_score + 0.3 * bm25_score) * source_boost
```

### 5.6 LLM Service (`llm_service/serve.py`)

```python
class PromptComposer:
    def compose_prompt(self, query: str, chunks: List[Dict]) -> str:
        # Format chunks as context
        context = "\n---\n".join([
            f"[{chunk['id']}] {chunk['title']}\n{chunk['chunk_text']}"
            for chunk in chunks
        ])
        
        # Insert into template
        return SYSTEM_PROMPT_TEMPLATE.format(context=context) + f"\nUser: {query}"

class LLMService:
    def answer_query(self, query: str, chunks: List[Dict]) -> str:
        prompt = self.prompt_composer.compose_prompt(query, chunks)
        
        # Call Ollama API
        response = self.client.post(
            f"{self.service_url}/v1/chat/completions",
            json={"model": self.model_name, "messages": [...], "max_tokens": 2048}
        )
        
        return response.json()["choices"][0]["message"]["content"]
```

---

## 6. Data Flow Explained

### 6.1 JSONL File Format

All data is stored in JSONL (JSON Lines) format - one JSON object per line:

**Raw data (`swc_docs_raw.jsonl`):**
```json
{"title": "Button", "body": "The sp-button component...", "code_blocks": ["<sp-button>Click</sp-button>"], "url": "https://..."}
{"title": "Popover", "body": "Popovers display content...", "code_blocks": [...], "url": "https://..."}
```

**Chunked data (`swc_docs_chunks.jsonl`):**
```json
{"id": "abc123_0", "source": "swc_docs", "title": "Button", "chunk_text": "The sp-button component...", "chunk_index": 0, "url": "https://..."}
{"id": "abc123_1", "source": "swc_docs", "title": "Button", "chunk_text": "To use the button...", "chunk_index": 1, "url": "https://..."}
```

### 6.2 Qdrant Payload Structure

Each vector in Qdrant has this payload:

```json
{
  "id": "abc123_0",
  "source": "swc_docs",          // or "github", "slack"
  "url": "https://...",
  "title": "Button Component",
  "heading_path": "Components > Button > Usage",
  "chunk_text": "The sp-button component...",
  "chunk_index": 0,
  "type": "text",
  "timestamp": "2025-12-11T10:30:00",
  "author": "unknown",
  "metadata": {"total_chunks": 5}
}
```

---

## 7. Code Walkthrough

### 7.1 Answering a Query (Step by Step)

**File:** `api/app.py` → `POST /answer`

```python
@app.post("/answer", response_model=AnswerResponse)
async def answer_query(request: AnswerRequest):
    # Step 1: Retrieve relevant chunks
    retrieved_chunks = retriever_service.retrieve(
        query=request.query,           # "How do I use sp-button?"
        top_k=50,                       # Get 50 candidates
        rerank_top_k=request.top_k     # Return top 5 after reranking
    )
    
    # Step 2: Generate answer with LLM
    answer = llm_service.answer_query(request.query, retrieved_chunks)
    
    # Step 3: Format response
    sources = [
        Source(
            title=chunk["payload"]["title"],
            url=chunk["payload"]["url"],
            snippet=chunk["payload"]["chunk_text"][:200],
            chunk_id=chunk["payload"]["id"]
        )
        for chunk in retrieved_chunks[:request.top_k]
    ]
    
    return AnswerResponse(answer=answer, sources=sources, ...)
```

### 7.2 Ingestion Pipeline (Step by Step)

**Trigger:** `POST /ingest/run`

```python
# Step 1: Crawl SWC Docs
crawler = SWCDocsCrawler()
results = crawler.crawl_from_file(urls_path)  # Read URLs, fetch pages
crawler.save_jsonl(results, "data/swc_docs_raw.jsonl")

# Step 2: Clone and Index GitHub
ingester = GitHubIngester()
results = ingester.ingest_repo("https://github.com/adobe/spectrum-web-components")
ingester.save_jsonl(results, "data/github_raw.jsonl")

# Step 3: Chunk the data
process_jsonl("data/swc_docs_raw.jsonl", "data/chunks/swc_docs_chunks.jsonl", "swc_docs")
process_jsonl("data/github_raw.jsonl", "data/chunks/github_chunks.jsonl", "github")

# Step 4: Compute embeddings and index
process_chunks_jsonl("data/chunks/swc_docs_chunks.jsonl", vector_client)
process_chunks_jsonl("data/chunks/github_chunks.jsonl", vector_client)
```

---

## 8. Development Workflow

### 8.1 Local Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd Spectrum-Sense

# 2. Start services
cd deploy
docker compose up -d

# 3. Download LLM model
docker exec spectrum-ollama ollama pull mistral:7b

# 4. Ingest data
curl -N -X POST http://localhost:8000/ingest/run/stream \
  -H "Content-Type: application/json" \
  -d '{"source": "all", "urls_file": "/app/sample_data/swc_urls.txt", "github_repo": "https://github.com/adobe/spectrum-web-components"}'

# 5. Open frontend
open http://localhost:3000
```

### 8.2 Making Code Changes

```bash
# 1. Edit Python files in api/, ingest/, embeddings/, etc.

# 2. Rebuild API container
cd deploy
docker compose build api

# 3. Restart
docker compose up -d api

# 4. Watch logs
docker logs -f spectrum-api
```

### 8.3 Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_e2e.py -v

# With coverage
pytest tests/ --cov=.
```

---

## 9. Common Tasks

### 9.1 Adding a New Data Source

1. Create ingester in `ingest/new_source_ingester.py`
2. Implement extraction logic (similar to `github_ingester.py`)
3. Add source to `ingest/normalize_and_chunk.py` choices
4. Update `api/app.py` ingestion endpoint
5. Add source boost in `retriever/service.py`

### 9.2 Changing the LLM Model

```bash
# Pull new model
docker exec spectrum-ollama ollama pull llama3:8b-instruct

# Update docker-compose.yml
environment:
  - LLM_MODEL=llama3:8b-instruct

# Restart
docker compose restart api
```

### 9.3 Adjusting Chunk Size

Edit `ingest/normalize_and_chunk.py`:

```python
chunker = Chunker(chunk_size=1500, chunk_overlap=300)  # Larger chunks
```

Then re-ingest data.

### 9.4 Tuning Source Boost

Edit `retriever/service.py`:

```python
SOURCE_BOOST = {
    "swc_docs": 1.5,   # Increase docs priority
    "github": 0.8,      # Decrease code priority
    "slack": 1.0,
}
```

---

## 10. Troubleshooting Guide

### Problem: "No results from vector search"

**Cause:** Qdrant has no indexed data.

**Solution:**
```bash
# Check points count
curl http://localhost:8000/health

# If 0 points, run ingestion
curl -X POST http://localhost:8000/ingest/run -d '{"source": "all", ...}'
```

### Problem: API container not starting

**Cause:** Dependency issues or code errors.

**Solution:**
```bash
# Check logs
docker logs spectrum-api

# Rebuild from scratch
docker compose build api --no-cache
docker compose up -d api
```

### Problem: LLM returning mock responses

**Cause:** Ollama not running or model not downloaded.

**Solution:**
```bash
# Check Ollama
curl http://localhost:11434/api/tags

# Download model
docker exec spectrum-ollama ollama pull mistral:7b
```

### Problem: Ingestion taking too long

**Cause:** Too many files/URLs.

**Solution:**
- Edit `sample_data/swc_urls.txt` to reduce URLs
- Modify `github_ingester.py` to skip more directories
- Cancel and restart: `curl -X POST http://localhost:8000/ingest/cancel`

---

## 11. Glossary

| Term | Definition |
|------|------------|
| **RAG** | Retrieval-Augmented Generation - combining retrieval with LLM generation |
| **Embedding** | Numerical vector representation of text |
| **Vector Database** | Database optimized for similarity search on vectors |
| **Chunk** | Small piece of a larger document |
| **BM25** | Best Matching 25 - keyword-based ranking algorithm |
| **JSONL** | JSON Lines - one JSON object per line |
| **Payload** | Metadata attached to a vector in Qdrant |
| **Token** | Smallest unit of text for LLMs (~4 characters) |
| **Ollama** | Tool for running LLMs locally |
| **CORS** | Cross-Origin Resource Sharing - allows frontend to call API |
| **SSE** | Server-Sent Events - streaming data from server to client |
| **Shallow Clone** | Git clone with only latest commit (`--depth 1`) |

---

## Next Steps

1. **Read the code**: Start with `api/app.py` → follow the imports
2. **Run locally**: Get the app working on your machine
3. **Experiment**: Change the prompt, adjust boost factors, try different models
4. **Ask questions**: Use this guide as a reference

**Happy Learning!**
