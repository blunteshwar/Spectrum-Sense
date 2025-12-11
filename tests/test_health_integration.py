"""Health check and integration tests for PR validation.

These tests verify that all services are healthy and working correctly.
Run these tests before merging PRs to ensure everything is functioning.
"""

import os
import pytest
import httpx
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

# Test configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b")


@pytest.fixture(scope="module")
def api_client():
    """Create HTTP client for API tests."""
    return httpx.Client(base_url=API_BASE_URL, timeout=30.0)


@pytest.fixture(scope="module")
def ollama_client():
    """Create HTTP client for Ollama tests."""
    return httpx.Client(base_url=OLLAMA_URL, timeout=30.0)


class TestServiceHealth:
    """Test that all services are healthy and accessible."""

    def test_qdrant_health(self):
        """Test that Qdrant is accessible and healthy."""
        try:
            response = httpx.get(f"{QDRANT_URL}/health", timeout=5.0)
            assert response.status_code == 200, f"Qdrant health check failed: {response.status_code}"
            health_data = response.json()
            assert health_data.get("status") == "ok", f"Qdrant not healthy: {health_data}"
        except httpx.ConnectError:
            pytest.fail("Cannot connect to Qdrant. Is it running?")

    def test_ollama_health(self, ollama_client):
        """Test that Ollama is accessible."""
        try:
            # Check if Ollama is responding
            response = ollama_client.get("/api/tags", timeout=5.0)
            assert response.status_code == 200, f"Ollama health check failed: {response.status_code}"
            
            # Check if the required model is available
            models_data = response.json()
            available_models = [model.get("name", "") for model in models_data.get("models", [])]
            
            # Check if our model (or a variant) is available
            model_found = any(
                OLLAMA_MODEL.split(":")[0] in model for model in available_models
            )
            assert model_found, (
                f"Required model '{OLLAMA_MODEL}' not found in Ollama. "
                f"Available models: {available_models}. "
                f"Run: docker exec spectrum-ollama ollama pull {OLLAMA_MODEL}"
            )
        except httpx.ConnectError:
            pytest.fail("Cannot connect to Ollama. Is it running?")

    def test_api_health(self, api_client):
        """Test that API health endpoint returns healthy status."""
        response = api_client.get("/health", timeout=10.0)
        assert response.status_code == 200, f"API health check failed: {response.status_code}"
        
        health_data = response.json()
        assert health_data.get("status") in ["healthy", "degraded"], \
            f"API status should be 'healthy' or 'degraded', got: {health_data.get('status')}"
        
        components = health_data.get("components", {})
        
        # Check Qdrant component
        assert "qdrant" in components, "Qdrant component not in health check"
        assert "error" not in components["qdrant"].lower(), \
            f"Qdrant component has error: {components['qdrant']}"
        
        # Check LLM component
        assert "llm" in components, "LLM component not in health check"
        assert components["llm"] == "healthy", \
            f"LLM component not healthy: {components['llm']}"
        
        # Check retriever component
        assert "retriever" in components, "Retriever component not in health check"
        assert components["retriever"] == "healthy", \
            f"Retriever component not healthy: {components['retriever']}"


class TestLLMIntegration:
    """Test that LLM service is properly integrated and not using mock."""

    def test_ollama_model_available(self, ollama_client):
        """Test that the required Ollama model is downloaded and available."""
        response = ollama_client.get("/api/tags", timeout=10.0)
        assert response.status_code == 200
        
        models_data = response.json()
        available_models = [model.get("name", "") for model in models_data.get("models", [])]
        
        # Check for model (exact match or variant)
        model_variants = [
            OLLAMA_MODEL,
            f"{OLLAMA_MODEL.split(':')[0]}:latest",
            OLLAMA_MODEL.split(":")[0]
        ]
        
        found = any(
            any(variant in model for variant in model_variants)
            for model in available_models
        )
        
        assert found, (
            f"Model '{OLLAMA_MODEL}' not available. "
            f"Available: {available_models}. "
            f"Run: docker exec spectrum-ollama ollama pull {OLLAMA_MODEL}"
        )

    def test_ollama_generate(self, ollama_client):
        """Test that Ollama can generate responses."""
        # Test with a simple prompt
        response = ollama_client.post(
            "/v1/chat/completions",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "user", "content": "Say 'test' if you can read this."}
                ],
                "max_tokens": 10
            },
            timeout=30.0
        )
        
        assert response.status_code == 200, \
            f"Ollama generation failed: {response.status_code} - {response.text}"
        
        result = response.json()
        assert "choices" in result, "Response missing 'choices' field"
        assert len(result["choices"]) > 0, "No choices in response"
        
        content = result["choices"][0].get("message", {}).get("content", "")
        assert len(content) > 0, "Empty response from Ollama"


class TestRAGIntegration:
    """Test the full RAG pipeline through the API."""

    def test_answer_endpoint_structure(self, api_client):
        """Test that /answer endpoint returns correct structure."""
        response = api_client.post(
            "/answer",
            json={
                "query": "What is Spectrum?",
                "top_k": 3
            },
            timeout=60.0  # LLM generation can take time
        )
        
        assert response.status_code == 200, \
            f"Answer endpoint failed: {response.status_code} - {response.text}"
        
        data = response.json()
        
        # Check response structure
        assert "answer" in data, "Response missing 'answer' field"
        assert "sources" in data, "Response missing 'sources' field"
        assert "used_snippet_ids" in data, "Response missing 'used_snippet_ids' field"
        assert "meta" in data, "Response missing 'meta' field"
        
        # Check answer is not empty
        assert len(data["answer"]) > 0, "Answer is empty"
        
        # Check answer is not a mock response
        mock_indicators = [
            "mock response",
            "configure a real llm",
            "this is a mock"
        ]
        answer_lower = data["answer"].lower()
        assert not any(indicator in answer_lower for indicator in mock_indicators), \
            f"Answer appears to be a mock response: {data['answer'][:200]}"
        
        # Check sources structure
        assert isinstance(data["sources"], list), "Sources should be a list"
        
        # Check meta contains latency
        assert "latency_ms" in data["meta"], "Meta missing latency_ms"
        assert isinstance(data["meta"]["latency_ms"], int), "latency_ms should be integer"

    def test_answer_with_no_results(self, api_client):
        """Test that /answer handles queries with no results gracefully."""
        response = api_client.post(
            "/answer",
            json={
                "query": "xyzabc123nonexistentquery987654",
                "top_k": 5
            },
            timeout=60.0
        )
        
        assert response.status_code == 200, \
            f"Answer endpoint failed: {response.status_code}"
        
        data = response.json()
        assert "answer" in data, "Response missing 'answer' field"
        # Should return a helpful message when no results found
        assert len(data["answer"]) > 0, "Answer should not be empty even with no results"


class TestIngestionIntegration:
    """Test ingestion endpoints."""

    def test_ingest_endpoint_structure(self, api_client):
        """Test that /ingest/run endpoint returns correct structure."""
        response = api_client.post(
            "/ingest/run",
            json={"source": "swc_docs"},
            timeout=120.0  # Ingestion can take time
        )
        
        assert response.status_code == 200, \
            f"Ingest endpoint failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "status" in data, "Response missing 'status' field"
        assert "task_id" in data, "Response missing 'task_id' field"
        assert data["status"] == "started", f"Expected status 'started', got: {data['status']}"


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow."""

    @pytest.mark.slow
    def test_full_rag_workflow(self, api_client):
        """Test complete RAG workflow: health -> query -> verify response."""
        # 1. Verify health
        health_response = api_client.get("/health", timeout=10.0)
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert health_data["status"] == "healthy", \
            f"Services not healthy: {health_data}"
        
        # 2. Make a query
        query_response = api_client.post(
            "/answer",
            json={
                "query": "How do I use Spectrum components?",
                "top_k": 5
            },
            timeout=60.0
        )
        
        assert query_response.status_code == 200, \
            f"Query failed: {query_response.status_code} - {query_response.text}"
        
        query_data = query_response.json()
        
        # 3. Verify response quality
        assert len(query_data["answer"]) > 50, \
            "Answer too short (might indicate LLM issue)"
        
        # 4. Verify latency is reasonable (less than 30 seconds)
        latency_ms = query_data["meta"].get("latency_ms", 0)
        assert latency_ms < 30000, \
            f"Latency too high: {latency_ms}ms (might indicate service issues)"
        
        # 5. Verify sources if available
        if len(query_data["sources"]) > 0:
            source = query_data["sources"][0]
            assert "title" in source, "Source missing title"
            assert "url" in source, "Source missing url"
            assert "snippet" in source, "Source missing snippet"


if __name__ == "__main__":
    # Allow running directly with: python -m pytest tests/test_health_integration.py -v
    pytest.main([__file__, "-v"])

