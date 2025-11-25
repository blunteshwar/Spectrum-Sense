"""Tests for embeddings computation."""

from embeddings.compute_embeddings import EmbeddingComputer


def test_embedding_computer():
    """Test embedding computation."""
    computer = EmbeddingComputer(model_name="sentence-transformers/all-mpnet-base-v2")
    
    text = "This is a test sentence."
    embedding = computer.compute_embedding(text)
    
    assert len(embedding) == 768  # all-mpnet-base-v2 dimension
    assert all(isinstance(x, float) for x in embedding)


def test_batch_embeddings():
    """Test batch embedding computation."""
    computer = EmbeddingComputer(model_name="sentence-transformers/all-mpnet-base-v2")
    
    texts = ["First sentence.", "Second sentence.", "Third sentence."]
    embeddings = computer.compute_batch(texts, batch_size=2)
    
    assert len(embeddings) == 3
    assert all(len(emb) == 768 for emb in embeddings)

