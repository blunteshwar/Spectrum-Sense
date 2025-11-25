"""FastAPI application for Spectrum RAG chatbot."""

import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog

# Import modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from vector.qdrant_client import QdrantClientWrapper
from embeddings.compute_embeddings import EmbeddingComputer
from retriever.service import RetrieverService
from llm_service.serve import create_llm_service, MockLLMService
from ingest.spectrum_crawler import SpectrumCrawler
from ingest.slack_importer import SlackImporter
from ingest.normalize_and_chunk import process_jsonl

logger = structlog.get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Spectrum RAG API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global services (initialized in startup)
vector_client: Optional[QdrantClientWrapper] = None
embedding_computer: Optional[EmbeddingComputer] = None
retriever_service: Optional[RetrieverService] = None
llm_service: Optional[MockLLMService] = None


# Request/Response models
class AnswerRequest(BaseModel):
    query: str = Field(..., description="User query")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    top_k: int = Field(5, description="Number of top results to return")


class Source(BaseModel):
    title: str
    heading_path: str
    url: str
    snippet: str
    chunk_id: str


class AnswerResponse(BaseModel):
    answer: str
    sources: List[Source]
    used_snippet_ids: List[str]
    meta: Dict[str, Any]


class IngestRequest(BaseModel):
    source: str = Field("all", description="Source to ingest: 'spectrum', 'slack', or 'all'")


class IngestResponse(BaseModel):
    status: str
    task_id: str


class HealthResponse(BaseModel):
    status: str
    components: Dict[str, str]


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global vector_client, embedding_computer, retriever_service, llm_service

    # Load configuration
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    collection_name = os.getenv("QDRANT_COLLECTION_NAME", "spectrum_docs")
    embedding_model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")
    llm_service_url = os.getenv("LLM_SERVICE_URL", "http://llm-mock:8001")
    use_mock_llm = os.getenv("USE_MOCK_LLM", "true").lower() == "true"

    # Initialize vector client
    logger.info("Initializing vector client", host=qdrant_host, port=qdrant_port)
    vector_client = QdrantClientWrapper(
        host=qdrant_host,
        port=qdrant_port,
        collection_name=collection_name
    )

    # Initialize embedding computer
    logger.info("Initializing embedding computer", model=embedding_model)
    embedding_computer = EmbeddingComputer(model_name=embedding_model)

    # Initialize retriever
    use_bm25 = os.getenv("USE_BM25_RERANKER", "true").lower() == "true"
    logger.info("Initializing retriever", use_bm25=use_bm25)
    retriever_service = RetrieverService(
        vector_client=vector_client,
        embedding_computer=embedding_computer,
        use_bm25_reranker=use_bm25
    )

    # Initialize LLM service
    if use_mock_llm:
        logger.info("Using mock LLM service")
        llm_service = MockLLMService()
    else:
        logger.info("Initializing LLM service", url=llm_service_url)
        llm_service = create_llm_service(service_url=llm_service_url, use_mock=False)

    logger.info("Startup complete")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    components = {}

    # Check Qdrant
    try:
        if vector_client:
            info = vector_client.get_collection_info()
            components["qdrant"] = f"healthy (points: {info.get('points_count', 0)})"
        else:
            components["qdrant"] = "not initialized"
    except Exception as e:
        components["qdrant"] = f"error: {str(e)}"

    # Check LLM
    if llm_service:
        components["llm"] = "healthy"
    else:
        components["llm"] = "not initialized"

    # Check retriever
    if retriever_service:
        components["retriever"] = "healthy"
    else:
        components["retriever"] = "not initialized"

    status = "healthy" if all("error" not in v.lower() for v in components.values()) else "degraded"

    return HealthResponse(status=status, components=components)


@app.post("/answer", response_model=AnswerResponse)
async def answer_query(request: AnswerRequest):
    """Answer a query using RAG."""
    if not retriever_service or not llm_service:
        raise HTTPException(status_code=503, detail="Services not initialized")

    start_time = time.time()

    try:
        # Retrieve relevant chunks
        top_k_retrieve = int(os.getenv("RETRIEVER_TOP_K", "50"))
        rerank_top_k = request.top_k

        retrieved_chunks = retriever_service.retrieve(
            query=request.query,
            top_k=top_k_retrieve,
            rerank_top_k=rerank_top_k
        )

        if not retrieved_chunks:
            return AnswerResponse(
                answer="I couldn't find any relevant information in the indexed Spectrum docs or Slack corpus.",
                sources=[],
                used_snippet_ids=[],
                meta={"latency_ms": int((time.time() - start_time) * 1000)}
            )

        # Generate answer using LLM
        answer = llm_service.answer_query(request.query, retrieved_chunks)

        # Extract sources
        sources = []
        used_snippet_ids = []

        for chunk in retrieved_chunks[:request.top_k]:
            payload = chunk.get("payload", {})
            chunk_id = str(payload.get("id", ""))
            title = payload.get("title", "Untitled")
            heading_path = payload.get("heading_path", "")
            url = payload.get("url", "")
            chunk_text = payload.get("chunk_text", "")

            # Create snippet (first 200 chars)
            snippet = chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text

            sources.append(Source(
                title=title,
                heading_path=heading_path,
                url=url,
                snippet=snippet,
                chunk_id=chunk_id
            ))
            used_snippet_ids.append(chunk_id)

        latency_ms = int((time.time() - start_time) * 1000)

        return AnswerResponse(
            answer=answer,
            sources=sources,
            used_snippet_ids=used_snippet_ids,
            meta={"latency_ms": latency_ms}
        )

    except Exception as e:
        logger.error("Error answering query", error=str(e), query=request.query)
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.post("/ingest/run", response_model=IngestResponse)
async def run_ingestion(request: IngestRequest):
    """Trigger ingestion pipeline."""
    task_id = f"ingest-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}"

    try:
        data_dir = Path(os.getenv("DATA_DIR", "./data"))
        chunks_dir = Path(os.getenv("CHUNKS_DIR", "./data/chunks"))
        sample_data_dir = Path(os.getenv("SAMPLE_DATA_DIR", "./sample_data"))

        if request.source in ["spectrum", "all"]:
            logger.info("Starting Spectrum ingestion", task_id=task_id)
            # For MVP, use sample data or crawl
            # In production, this would be async
            crawler = SpectrumCrawler(max_pages=10)  # Limit for dev
            results = crawler.crawl()
            spectrum_output = data_dir / "spectrum_raw.jsonl"
            crawler.save_jsonl(results, spectrum_output)

            # Chunk
            spectrum_chunks = chunks_dir / "spectrum_chunks.jsonl"
            process_jsonl(spectrum_output, spectrum_chunks, "spectrum")

            # Index (would be async in production)
            from embeddings.compute_embeddings import process_chunks_jsonl
            if vector_client:
                process_chunks_jsonl(spectrum_chunks, vector_client)

        if request.source in ["slack", "all"]:
            logger.info("Starting Slack ingestion", task_id=task_id)
            
            # Check for custom Slack export path, fallback to sample data
            slack_export_path_env = os.getenv("SLACK_EXPORT_PATH")
            if slack_export_path_env:
                slack_export_path = Path(slack_export_path_env)
            else:
                slack_export_path = sample_data_dir / "slack_sample.json"
            
            if not slack_export_path.exists():
                error_msg = f"Slack export path not found: {slack_export_path}. " \
                           f"Set SLACK_EXPORT_PATH environment variable or place export in {sample_data_dir}/slack_sample.json"
                logger.error(error_msg)
                raise HTTPException(status_code=404, detail=error_msg)
            
            logger.info("Processing Slack export", path=str(slack_export_path))
            importer = SlackImporter()
            results = importer.parse_slack_export(slack_export_path)
            slack_output = data_dir / "slack_raw.jsonl"
            importer.save_jsonl(results, slack_output)
            
            logger.info("Processed Slack threads", count=len(results))

            # Chunk
            slack_chunks = chunks_dir / "slack_chunks.jsonl"
            process_jsonl(slack_output, slack_chunks, "slack")

            # Index
            from embeddings.compute_embeddings import process_chunks_jsonl
            if vector_client:
                process_chunks_jsonl(slack_chunks, vector_client)
                logger.info("Indexed Slack chunks")

        return IngestResponse(status="started", task_id=task_id)

    except Exception as e:
        logger.error("Error running ingestion", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error running ingestion: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

