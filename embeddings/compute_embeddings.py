"""Compute embeddings for chunks and write to vector DB."""

import json
from pathlib import Path
from typing import List, Dict, Optional

from sentence_transformers import SentenceTransformer
import structlog

logger = structlog.get_logger(__name__)


class EmbeddingComputer:
    """Computes embeddings using sentence-transformers."""

    def __init__(self, model_name: str = "sentence-transformers/all-mpnet-base-v2"):
        logger.info("Loading embedding model", model=model_name)
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info("Model loaded", dimension=self.dimension)

    def compute_embedding(self, text: str) -> List[float]:
        """Compute embedding for a single text."""
        return self.model.encode(text, convert_to_numpy=True).tolist()

    def compute_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Compute embeddings for a batch of texts."""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        return embeddings.tolist()


def process_chunks_jsonl(
    input_path: Path,
    vector_client,  # QdrantClient wrapper
    model_name: str = "sentence-transformers/all-mpnet-base-v2",
    batch_size: int = 32
) -> int:
    """Process chunks JSONL file and upsert to vector DB."""
    computer = EmbeddingComputer(model_name)

    chunks = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))

    logger.info("Processing chunks", count=len(chunks))

    # Process in batches
    total_upserted = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [chunk["chunk_text"] for chunk in batch]

        # Compute embeddings
        embeddings = computer.compute_batch(texts, batch_size=batch_size)

        # Prepare vectors and payloads
        vectors = []
        payloads = []
        for chunk, embedding in zip(batch, embeddings):
            vectors.append(embedding)
            payloads.append({
                "id": chunk["id"],
                "source": chunk["source"],
                "url": chunk["url"],
                "title": chunk["title"],
                "heading_path": chunk["heading_path"],
                "chunk_index": chunk["chunk_index"],
                "chunk_text": chunk["chunk_text"],
                "type": chunk["type"],
                "timestamp": chunk["timestamp"],
                "author": chunk.get("author", "unknown"),
                "metadata": chunk.get("metadata", {}),
            })

        # Upsert to vector DB
        vector_client.upsert_batch(vectors, payloads)
        total_upserted += len(batch)
        logger.info("Upserted batch", batch=i // batch_size + 1, total=total_upserted)

    return total_upserted


def main():
    """CLI entry point."""
    import argparse
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from vector.qdrant_client import QdrantClientWrapper

    parser = argparse.ArgumentParser(description="Compute embeddings and index chunks")
    parser.add_argument("input", type=Path, help="Input chunks JSONL path")
    parser.add_argument("--model", default="sentence-transformers/all-mpnet-base-v2", help="Embedding model name")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--qdrant-host", default="localhost", help="Qdrant host")
    parser.add_argument("--qdrant-port", type=int, default=6333, help="Qdrant port")
    parser.add_argument("--collection", default="spectrum_docs", help="Collection name")

    args = parser.parse_args()

    # Initialize vector client
    vector_client = QdrantClientWrapper(
        host=args.qdrant_host,
        port=args.qdrant_port,
        collection_name=args.collection
    )

    # Process chunks
    total = process_chunks_jsonl(
        args.input,
        vector_client,
        model_name=args.model,
        batch_size=args.batch_size
    )

    print(f"Indexed {total} chunks")


if __name__ == "__main__":
    main()

