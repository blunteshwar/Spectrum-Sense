# Design Notes

## Architecture Overview

The Spectrum RAG backend follows a modular pipeline architecture:

1. **Ingestion** → Raw content extraction
2. **Chunking** → Text normalization and splitting
3. **Embedding** → Vector representation
4. **Indexing** → Vector DB storage
5. **Retrieval** → Semantic search + re-ranking
6. **Generation** → LLM answer synthesis

## Chunking Strategy

### Chunk Size: 1000 characters
- **Rationale**: Balances context preservation with retrieval precision
- **Overlap**: 200 characters (20%)
- **Rationale**: Ensures continuity across chunk boundaries

### Code Block Preservation
- Code blocks are extracted and preserved as separate entities
- Placeholders used during chunking to maintain code integrity
- Code blocks restored in final chunks

### Metadata Fields
- `id`: Unique chunk identifier (hash-based)
- `source`: "spectrum" or "slack"
- `url`: Source URL or thread identifier
- `title`: Document/thread title
- `heading_path`: Hierarchical heading path
- `chunk_index`: Position in document
- `chunk_text`: Actual chunk content
- `type`: "text" or "code"
- `timestamp`: Creation timestamp
- `author`: Document author or Slack user

## Embedding Model Choice

### Model: `sentence-transformers/all-mpnet-base-v2`
- **Dimension**: 768
- **Rationale**:
  - Strong performance on semantic similarity tasks
  - Good balance of quality and speed
  - Well-suited for technical documentation
  - 420MB download size (reasonable)

### Alternatives Considered
- `all-MiniLM-L6-v2`: Smaller (384 dim) but lower quality
- `all-mpnet-base-v2`: Chosen for best quality/size tradeoff
- `multi-qa-mpnet-base`: Optimized for Q&A but less general

## Vector Database: Qdrant

### Why Qdrant?
- Open-source and self-hostable
- Good Python client
- Efficient cosine similarity search
- Supports metadata filtering
- Easy Docker deployment

### Collection Configuration
- **Distance**: Cosine similarity
- **Vector size**: 768 (matches embedding model)
- **Index**: HNSW (default, efficient approximate search)

## Retrieval Strategy

### Two-Stage Retrieval

1. **Vector Search** (top-50)
   - Semantic similarity using cosine distance
   - Fast approximate search via HNSW index

2. **BM25 Re-ranking** (top-5)
   - Lexical matching for precision
   - Weighted combination: 70% vector + 30% BM25
   - Improves relevance for exact term matches

### Rationale
- Vector search captures semantic similarity
- BM25 captures exact keyword matches
- Combination improves overall relevance
- Top-50 → Top-5 reduces LLM context size

## Prompt Template

### System Prompt Structure
```
You are SpectrumGPT — an assistant restricted to answering only from the provided retrieved passages.

Rules:
1. Use only the retrieved passages for Spectrum-specific facts.
2. Cite every factual claim with the snippet source in brackets: [title — heading — url].
3. Preserve code blocks and include them verbatim with citations.
4. At the end include a "Sources" section listing used snippets.
5. Do not hallucinate versions, commits, or private user data.

Retrieved passages:
{context}

User question: {query}

Answer:
```

### Token Budget Management
- **Max context tokens**: 3000
- **Estimate**: ~4 characters per token
- **Max context chars**: ~12,000 characters
- Chunks added until budget reached
- Ensures prompt fits within model limits

## LLM Configuration

### Default Settings
- **Temperature**: 0.0 (deterministic answers)
- **Max tokens**: 1024
- **Stop sequences**: ["Sources:", "\n\nSources:"]

### Mock Service
- Returns structured mock responses
- Includes source citations
- Useful for local development without GPU

### Production Options

**Option A: GPU (text-generation-inference)**
- Supports Mistral-7B, Llama-2-13B
- Fast inference with GPU acceleration
- Requires NVIDIA GPU

**Option B: CPU (llama.cpp)**
- Quantized models (4-bit, 8-bit)
- Runs on CPU (slower but accessible)
- Good for development/testing

## PII Redaction

### Redacted Patterns
- **Emails**: `user@example.com` → `EMAIL_<hash>`
- **Phone numbers**: `555-123-4567` → `PHONE_<hash>`
- **IP addresses**: `192.168.1.1` → `IP_<hash>`
- **User mentions**: `@U12345` → `USER_<hash>`
- **Tokens**: Long alphanumeric strings → `TOKEN_<hash>`

### Redaction Report
- JSONL file listing all redactions
- Includes type, original (truncated), replacement
- Enables human review and audit

## API Design

### RESTful Endpoints
- `POST /answer`: Main query endpoint
- `POST /ingest/run`: Trigger ingestion
- `GET /health`: Health check

### Response Format
- Consistent JSON structure
- Includes sources with metadata
- Latency tracking in meta field
- Error handling with appropriate HTTP codes

### Streaming (Future)
- Placeholder for streaming responses
- Would use Server-Sent Events (SSE)
- Useful for long-form answers

## Testing Strategy

### Unit Tests
- Individual component testing
- Mock dependencies where needed
- Fast execution

### Integration Tests
- Component interaction testing
- Real Qdrant instance (Docker)

### E2E Smoke Test
- Full pipeline: ingest → index → query
- Uses sample data
- Validates end-to-end functionality

## Performance Considerations

### Embedding Computation
- Batch processing (default: 32 chunks)
- Progress bars for visibility
- Can be parallelized further if needed

### Vector Search
- HNSW index for fast approximate search
- Configurable top-k
- Score threshold filtering

### LLM Inference
- Mock service: <100ms
- Real LLM: 1-5s depending on model/hardware
- Token budget limits context size

## Security & Privacy

### PII Redaction
- Mandatory for Slack imports
- Hash-based replacement (not reversible)
- Audit trail via redaction report

### API Security
- CORS configured (adjust for production)
- Input validation via Pydantic
- Error messages don't leak internals

### Data Storage
- Local development: files on disk
- Production: Consider encryption at rest
- Vector DB: No sensitive data in vectors

## Scalability Considerations

### Current Limitations
- Single-threaded ingestion
- Synchronous API calls
- No job queue for ingestion

### Future Improvements
- Async ingestion with Celery/Redis
- Batch API endpoints
- Caching for frequent queries
- Horizontal scaling of API servers

## Monitoring & Observability

### Logging
- Structured logging with `structlog`
- JSON format for parsing
- Log levels: INFO, WARNING, ERROR

### Metrics (Future)
- Query latency
- Retrieval quality (MRR, NDCG)
- LLM token usage
- Error rates

## Deployment

### Docker Compose
- Single-file deployment
- Service dependencies handled
- Volume mounts for data persistence

### Production Considerations
- Use managed Qdrant or self-hosted cluster
- Load balancer for API
- Monitoring (Prometheus, Grafana)
- Log aggregation (ELK, Loki)

