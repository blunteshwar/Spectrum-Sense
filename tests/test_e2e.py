"""End-to-end smoke test."""

import json
import tempfile
from pathlib import Path
import pytest
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from ingest.spectrum_crawler import SpectrumCrawler
from ingest.slack_importer import SlackImporter
from ingest.normalize_and_chunk import process_jsonl
from vector.qdrant_client import QdrantClientWrapper
from embeddings.compute_embeddings import EmbeddingComputer, process_chunks_jsonl
from retriever.service import RetrieverService


@pytest.mark.skipif(
    not Path(__file__).parent.parent.joinpath("sample_data").exists(),
    reason="Sample data not available"
)
def test_e2e_smoke():
    """End-to-end smoke test: ingest, index, query."""
    # This test requires Qdrant to be running
    # Skip if Qdrant is not available
    try:
        vector_client = QdrantClientWrapper(
            host="localhost",
            port=6333,
            collection_name="test_e2e",
            dimension=768
        )
    except Exception as e:
        pytest.skip(f"Qdrant not available: {e}")

    # Use sample data
    sample_dir = Path(__file__).parent.parent / "sample_data"
    
    # Process Spectrum sample
    spectrum_html = sample_dir / "spectrum_sample_1.html"
    if spectrum_html.exists():
        # Create a simple JSONL from HTML (simplified for test)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            doc = {
                "title": "sp-popover Component",
                "heading_path": "Components > Popover > Usage",
                "body": "The Popover component displays floating content. When opening a popover on pointerdown, ensure to set the placement prop correctly.",
                "code_blocks": [],
                "url": "https://spectrum.adobe.com/components/popover"
            }
            json.dump(doc, f)
            f.write("\n")
            temp_jsonl = Path(f.name)
        
        try:
            # Chunk
            chunks_path = tempfile.mktemp(suffix='.jsonl')
            process_jsonl(temp_jsonl, Path(chunks_path), "swc_docs")
            
            # Index
            embedding_computer = EmbeddingComputer()
            process_chunks_jsonl(Path(chunks_path), vector_client)
            
            # Query
            retriever = RetrieverService(
                vector_client=vector_client,
                embedding_computer=embedding_computer,
                use_bm25_reranker=False
            )
            
            results = retriever.retrieve("How do I use sp-popover with pointerdown?", top_k=5)
            
            assert len(results) > 0
            # Check that we found relevant content
            found_popover = any(
                "popover" in str(result.get("payload", {})).lower()
                for result in results
            )
            assert found_popover, "Should find popover-related content"
            
        finally:
            if temp_jsonl.exists():
                temp_jsonl.unlink()
            if Path(chunks_path).exists():
                Path(chunks_path).unlink()
            
            # Cleanup
            try:
                vector_client.delete_collection()
            except:
                pass

