"""FastAPI application for Spectrum RAG chatbot."""

import os
import time
import asyncio
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, AsyncGenerator
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import structlog

# Import modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from vector.qdrant_client import QdrantClientWrapper
from embeddings.compute_embeddings import EmbeddingComputer
from retriever.service import RetrieverService
from llm_service.serve import create_llm_service, MockLLMService, LLMService
from ingest.slack_importer import SlackImporter
from ingest.swc_docs_crawler import SWCDocsCrawler
from ingest.github_ingester import GitHubIngester
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
llm_service: Optional[Union[LLMService, MockLLMService]] = None

# Ingestion state tracking
ingestion_state: Dict[str, Any] = {
    "is_running": False,
    "task_id": None,
    "cancel_requested": False,
    "started_at": None
}


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
    source: str = Field("all", description="Source to ingest: 'swc_docs', 'github', 'slack', or 'all'")
    urls_file: Optional[str] = Field(None, description="Path to URLs file for swc_docs ingestion")
    github_repo: Optional[str] = Field(None, description="GitHub repo URL for github ingestion")
    github_branch: Optional[str] = Field("main", description="Branch to clone for github ingestion")


class IngestResponse(BaseModel):
    status: str
    task_id: str


class HealthResponse(BaseModel):
    status: str
    components: Dict[str, str]


class IngestStatusResponse(BaseModel):
    is_running: bool
    task_id: Optional[str]
    started_at: Optional[str]
    cancel_requested: bool


class IngestCancelResponse(BaseModel):
    status: str
    message: str
    task_id: Optional[str]


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global vector_client, embedding_computer, retriever_service, llm_service

    # Load configuration
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    collection_name = os.getenv("QDRANT_COLLECTION_NAME", "spectrum_docs")
    embedding_model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")
    llm_service_url = os.getenv("LLM_SERVICE_URL", "http://ollama:11434")
    llm_model = os.getenv("LLM_MODEL", "mistral:7b")
    use_mock_llm = os.getenv("USE_MOCK_LLM", "false").lower() == "true"

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
        logger.info("Initializing LLM service", url=llm_service_url, model=llm_model)
        llm_service = create_llm_service(service_url=llm_service_url, model_name=llm_model, use_mock=False)

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

        if request.source in ["swc_docs", "all"]:
            logger.info("Starting SWC docs ingestion", task_id=task_id)
            
            # Get URLs file path
            urls_file_path = request.urls_file or os.getenv("SWC_DOCS_URLS_FILE")
            if not urls_file_path:
                urls_file_path = str(sample_data_dir / "swc_urls.txt")
            
            urls_path = Path(urls_file_path)
            if not urls_path.exists():
                error_msg = f"SWC docs URLs file not found: {urls_path}. " \
                           f"Provide urls_file in request or set SWC_DOCS_URLS_FILE env var"
                logger.error(error_msg)
                raise HTTPException(status_code=404, detail=error_msg)
            
            logger.info("Crawling SWC docs", urls_file=str(urls_path))
            crawler = SWCDocsCrawler()
            results = crawler.crawl_from_file(urls_path)
            swc_docs_output = data_dir / "swc_docs_raw.jsonl"
            crawler.save_jsonl(results, swc_docs_output)
            
            logger.info("Crawled SWC docs pages", count=len(results))

            # Chunk
            swc_docs_chunks = chunks_dir / "swc_docs_chunks.jsonl"
            process_jsonl(swc_docs_output, swc_docs_chunks, "swc_docs")

            # Index
            from embeddings.compute_embeddings import process_chunks_jsonl
            if vector_client:
                process_chunks_jsonl(swc_docs_chunks, vector_client)
                logger.info("Indexed SWC docs chunks")

        if request.source in ["github", "all"]:
            logger.info("Starting GitHub ingestion", task_id=task_id)
            
            # Get repo URL
            repo_url = request.github_repo or os.getenv("GITHUB_REPO_URL", "https://github.com/adobe/spectrum-web-components")
            branch = request.github_branch or os.getenv("GITHUB_BRANCH", "main")
            clone_dir = os.getenv("GITHUB_CLONE_DIR", "./repos")
            
            logger.info("Ingesting GitHub repo", repo=repo_url, branch=branch)
            ingester = GitHubIngester(
                extensions={".ts", ".js", ".md", ".css"},
                clone_dir=clone_dir
            )
            results = ingester.ingest_repo(repo_url, branch=branch)
            github_output = data_dir / "github_raw.jsonl"
            ingester.save_jsonl(results, github_output)
            
            logger.info("Ingested GitHub files", count=len(results))

            # Chunk
            github_chunks = chunks_dir / "github_chunks.jsonl"
            process_jsonl(github_output, github_chunks, "github")

            # Index
            from embeddings.compute_embeddings import process_chunks_jsonl
            if vector_client:
                process_chunks_jsonl(github_chunks, vector_client)
                logger.info("Indexed GitHub chunks")

        return IngestResponse(status="started", task_id=task_id)

    except Exception as e:
        logger.error("Error running ingestion", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error running ingestion: {str(e)}")


async def stream_log(message: str, level: str = "info", **extra) -> str:
    """Format a log message for SSE streaming."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message,
        **extra
    }
    return f"data: {json.dumps(log_entry)}\n\n"


async def check_cancellation() -> bool:
    """Check if cancellation was requested."""
    return ingestion_state["cancel_requested"]


async def run_ingestion_with_logs(request: IngestRequest) -> AsyncGenerator[str, None]:
    """Run ingestion pipeline with streaming logs."""
    global ingestion_state
    
    # Check if already running
    if ingestion_state["is_running"]:
        yield await stream_log("Ingestion already in progress", level="error", 
                               existing_task_id=ingestion_state["task_id"])
        return
    
    task_id = f"ingest-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}"
    
    # Set ingestion state
    ingestion_state["is_running"] = True
    ingestion_state["task_id"] = task_id
    ingestion_state["cancel_requested"] = False
    ingestion_state["started_at"] = datetime.now().isoformat()
    
    yield await stream_log(f"Starting ingestion pipeline", level="info", task_id=task_id)
    
    try:
        data_dir = Path(os.getenv("DATA_DIR", "./data"))
        chunks_dir = Path(os.getenv("CHUNKS_DIR", "./data/chunks"))
        sample_data_dir = Path(os.getenv("SAMPLE_DATA_DIR", "./sample_data"))

        # Slack ingestion
        if request.source in ["slack", "all"]:
            if await check_cancellation():
                yield await stream_log("Ingestion cancelled by user", level="warning", task_id=task_id)
                return
            yield await stream_log("Starting Slack ingestion", level="info", source="slack")
            
            slack_export_path_env = os.getenv("SLACK_EXPORT_PATH")
            if slack_export_path_env:
                slack_export_path = Path(slack_export_path_env)
            else:
                slack_export_path = sample_data_dir / "slack_sample.json"
            
            if not slack_export_path.exists():
                yield await stream_log(f"Slack export not found: {slack_export_path}", level="warning")
            else:
                yield await stream_log(f"Processing Slack export: {slack_export_path}", level="info")
                
                importer = SlackImporter()
                results = importer.parse_slack_export(slack_export_path)
                slack_output = data_dir / "slack_raw.jsonl"
                importer.save_jsonl(results, slack_output)
                
                yield await stream_log(f"Processed {len(results)} Slack threads", level="info")

                # Chunk
                yield await stream_log("Chunking Slack data...", level="info")
                slack_chunks = chunks_dir / "slack_chunks.jsonl"
                process_jsonl(slack_output, slack_chunks, "slack")
                yield await stream_log("Slack chunking complete", level="info")

                # Index
                yield await stream_log("Indexing Slack chunks to vector store...", level="info")
                from embeddings.compute_embeddings import process_chunks_jsonl
                if vector_client:
                    process_chunks_jsonl(slack_chunks, vector_client)
                    yield await stream_log("Slack chunks indexed successfully", level="success")
                else:
                    yield await stream_log("Vector client not available, skipping indexing", level="warning")

        # SWC docs ingestion
        if request.source in ["swc_docs", "all"]:
            if await check_cancellation():
                yield await stream_log("Ingestion cancelled by user", level="warning", task_id=task_id)
                return
            yield await stream_log("Starting SWC docs ingestion", level="info", source="swc_docs")
            
            urls_file_path = request.urls_file or os.getenv("SWC_DOCS_URLS_FILE")
            if not urls_file_path:
                urls_file_path = str(sample_data_dir / "swc_urls.txt")
            
            urls_path = Path(urls_file_path)
            if not urls_path.exists():
                yield await stream_log(f"SWC docs URLs file not found: {urls_path}", level="error")
            else:
                yield await stream_log(f"Crawling SWC docs from: {urls_path}", level="info")
                
                crawler = SWCDocsCrawler()
                
                # Read URLs to show progress
                with open(urls_path, 'r') as f:
                    urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                yield await stream_log(f"Found {len(urls)} URLs to crawl", level="info")
                
                results = []
                for i, url in enumerate(urls, 1):
                    # Check for cancellation
                    if await check_cancellation():
                        yield await stream_log("Ingestion cancelled by user", level="warning", task_id=task_id)
                        ingestion_state["is_running"] = False
                        ingestion_state["task_id"] = None
                        return
                    
                    yield await stream_log(f"Crawling [{i}/{len(urls)}]: {url}", level="info")
                    try:
                        page_results = crawler.crawl_urls([url])
                        results.extend(page_results)
                        await asyncio.sleep(0)  # Allow other tasks to run
                    except Exception as e:
                        yield await stream_log(f"Error crawling {url}: {str(e)}", level="warning")
                
                swc_docs_output = data_dir / "swc_docs_raw.jsonl"
                crawler.save_jsonl(results, swc_docs_output)
                
                yield await stream_log(f"Crawled {len(results)} SWC docs pages", level="info")

                # Chunk
                yield await stream_log("Chunking SWC docs data...", level="info")
                swc_docs_chunks = chunks_dir / "swc_docs_chunks.jsonl"
                process_jsonl(swc_docs_output, swc_docs_chunks, "swc_docs")
                yield await stream_log("SWC docs chunking complete", level="info")

                # Index
                yield await stream_log("Indexing SWC docs chunks to vector store...", level="info")
                from embeddings.compute_embeddings import process_chunks_jsonl
                if vector_client:
                    process_chunks_jsonl(swc_docs_chunks, vector_client)
                    yield await stream_log("SWC docs chunks indexed successfully", level="success")
                else:
                    yield await stream_log("Vector client not available, skipping indexing", level="warning")

        # GitHub ingestion
        if request.source in ["github", "all"]:
            if await check_cancellation():
                yield await stream_log("Ingestion cancelled by user", level="warning", task_id=task_id)
                return
            yield await stream_log("Starting GitHub ingestion", level="info", source="github")
            
            repo_url = request.github_repo or os.getenv("GITHUB_REPO_URL", "https://github.com/adobe/spectrum-web-components")
            branch = request.github_branch or os.getenv("GITHUB_BRANCH", "main")
            clone_dir = os.getenv("GITHUB_CLONE_DIR", "./repos")
            
            yield await stream_log(f"Cloning/updating repo: {repo_url} (branch: {branch})", level="info")
            
            ingester = GitHubIngester(
                extensions={".ts", ".js", ".md", ".css"},
                clone_dir=clone_dir
            )
            
            yield await stream_log("Ingesting repository files...", level="info")
            results = ingester.ingest_repo(repo_url, branch=branch)
            github_output = data_dir / "github_raw.jsonl"
            ingester.save_jsonl(results, github_output)
            
            yield await stream_log(f"Ingested {len(results)} GitHub files", level="info")

            # Chunk
            yield await stream_log("Chunking GitHub data...", level="info")
            github_chunks = chunks_dir / "github_chunks.jsonl"
            process_jsonl(github_output, github_chunks, "github")
            yield await stream_log("GitHub chunking complete", level="info")

            # Index
            yield await stream_log("Indexing GitHub chunks to vector store...", level="info")
            from embeddings.compute_embeddings import process_chunks_jsonl
            if vector_client:
                process_chunks_jsonl(github_chunks, vector_client)
                yield await stream_log("GitHub chunks indexed successfully", level="success")
            else:
                yield await stream_log("Vector client not available, skipping indexing", level="warning")

        yield await stream_log("Ingestion pipeline completed successfully!", level="success", task_id=task_id)

    except Exception as e:
        yield await stream_log(f"Error during ingestion: {str(e)}", level="error")
    finally:
        # Reset ingestion state
        ingestion_state["is_running"] = False
        ingestion_state["task_id"] = None
        ingestion_state["cancel_requested"] = False


@app.post("/ingest/run/stream")
async def run_ingestion_stream(request: IngestRequest):
    """Trigger ingestion pipeline with streaming logs (SSE)."""
    return StreamingResponse(
        run_ingestion_with_logs(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/ingest/status", response_model=IngestStatusResponse)
async def get_ingestion_status():
    """Get the current ingestion status."""
    return IngestStatusResponse(
        is_running=ingestion_state["is_running"],
        task_id=ingestion_state["task_id"],
        started_at=ingestion_state["started_at"],
        cancel_requested=ingestion_state["cancel_requested"]
    )


@app.post("/ingest/cancel", response_model=IngestCancelResponse)
async def cancel_ingestion():
    """Cancel a running ingestion pipeline."""
    global ingestion_state
    
    if not ingestion_state["is_running"]:
        return IngestCancelResponse(
            status="no_op",
            message="No ingestion is currently running",
            task_id=None
        )
    
    if ingestion_state["cancel_requested"]:
        return IngestCancelResponse(
            status="pending",
            message="Cancellation already requested, waiting for current operation to complete",
            task_id=ingestion_state["task_id"]
        )
    
    # Request cancellation
    ingestion_state["cancel_requested"] = True
    logger.info("Ingestion cancellation requested", task_id=ingestion_state["task_id"])
    
    return IngestCancelResponse(
        status="cancelled",
        message="Cancellation requested. The ingestion will stop after the current operation completes.",
        task_id=ingestion_state["task_id"]
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

