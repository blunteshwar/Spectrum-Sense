"""Tests for vector DB operations."""

import pytest
from vector.qdrant_client import QdrantClientWrapper


@pytest.fixture
def vector_client():
    """Create a test vector client."""
    # Use a test collection name
    client = QdrantClientWrapper(
        host="localhost",
        port=6333,
        collection_name="test_spectrum_docs",
        dimension=768
    )
    yield client
    # Cleanup: delete test collection
    try:
        client.delete_collection()
    except:
        pass


def test_vector_upsert(vector_client):
    """Test vector upsert."""
    vectors = [[0.1] * 768]
    payloads = [{
        "id": "test_1",
        "title": "Test Document",
        "chunk_text": "This is a test chunk"
    }]
    
    vector_client.upsert_batch(vectors, payloads)
    
    # Verify upsert worked (no exception raised)
    assert True


def test_vector_search(vector_client):
    """Test vector search."""
    # First upsert some test data
    vectors = [[0.1] * 768, [0.2] * 768]
    payloads = [
        {"id": "test_1", "title": "Doc 1", "chunk_text": "First document"},
        {"id": "test_2", "title": "Doc 2", "chunk_text": "Second document"}
    ]
    vector_client.upsert_batch(vectors, payloads)
    
    # Search
    query_vector = [0.15] * 768
    results = vector_client.search(query_vector, top_k=2)
    
    assert len(results) > 0
    assert "score" in results[0]
    assert "payload" in results[0]

