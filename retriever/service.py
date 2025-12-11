"""Retriever service with optional BM25 re-ranking."""

from typing import List, Dict, Optional
from rank_bm25 import BM25Okapi
import structlog

logger = structlog.get_logger(__name__)


class RetrieverService:
    """Retrieves and optionally re-ranks chunks."""

    # Source-based boost factors for ranking
    # Higher values = higher priority in search results
    SOURCE_BOOST = {
        "swc_docs": 1.3,   # 30% boost for documentation
        "github": 1.0,      # No boost for code
        "slack": 1.1,       # Slight boost for Slack discussions
    }

    def __init__(
        self,
        vector_client,  # QdrantClientWrapper
        embedding_computer,  # EmbeddingComputer
        use_bm25_reranker: bool = True,
        source_boost: Optional[Dict[str, float]] = None
    ):
        self.vector_client = vector_client
        self.embedding_computer = embedding_computer
        self.use_bm25_reranker = use_bm25_reranker
        self.source_boost = source_boost or self.SOURCE_BOOST
        self.bm25_index = None
        self.bm25_corpus = []

    def _build_bm25_index(self, chunks: List[Dict]):
        """Build BM25 index from chunks."""
        if not chunks:
            return

        # Tokenize chunks for BM25
        corpus = []
        for chunk in chunks:
            text = chunk.get("payload", {}).get("chunk_text", "")
            # Simple tokenization (split on whitespace and punctuation)
            tokens = text.lower().split()
            corpus.append(tokens)

        if corpus:
            self.bm25_index = BM25Okapi(corpus)
            self.bm25_corpus = chunks
            logger.info("Built BM25 index", corpus_size=len(corpus))

    def retrieve(
        self,
        query: str,
        top_k: int = 50,
        rerank_top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Retrieve chunks for a query.

        Args:
            query: Query string
            top_k: Number of initial results from vector search
            rerank_top_k: Number of results after re-ranking (if None, uses top_k)
            score_threshold: Minimum similarity score
            filter_dict: Optional filters for vector search

        Returns:
            List of ranked chunks with scores
        """
        # Compute query embedding
        query_vector = self.embedding_computer.compute_embedding(query)

        # Vector search
        results = self.vector_client.search(
            query_vector=query_vector,
            top_k=top_k,
            score_threshold=score_threshold,
            filter_dict=filter_dict
        )

        if not results:
            logger.warning("No results from vector search", query=query[:50])
            return []

        logger.info("Vector search results", count=len(results), query=query[:50])

        # Re-rank with BM25 if enabled
        if self.use_bm25_reranker and len(results) > 1:
            rerank_k = rerank_top_k or top_k
            reranked = self._rerank_bm25(query, results, rerank_k)
            return reranked

        return results[:rerank_top_k or top_k]

    def _rerank_bm25(
        self,
        query: str,
        results: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """Re-rank results using BM25."""
        if not self.bm25_index or not self.bm25_corpus:
            # Build index from current results
            self._build_bm25_index(results)

        if not self.bm25_index:
            logger.warning("BM25 index not available, returning original results")
            return results[:top_k]

        # Tokenize query
        query_tokens = query.lower().split()

        # Get BM25 scores
        bm25_scores = self.bm25_index.get_scores(query_tokens)

        # Combine vector scores with BM25 scores
        # Normalize and combine (simple weighted average)
        combined_results = []
        for i, result in enumerate(results):
            vector_score = result.get("score", 0.0)
            bm25_score = bm25_scores[i] if i < len(bm25_scores) else 0.0

            # Normalize BM25 score (rough normalization)
            normalized_bm25 = min(bm25_score / 10.0, 1.0) if bm25_score > 0 else 0.0

            # Weighted combination (70% vector, 30% BM25)
            combined_score = 0.7 * vector_score + 0.3 * normalized_bm25

            # Apply source-based boost (docs get higher priority than code)
            source = result.get("payload", {}).get("source", "")
            source_boost = self.source_boost.get(source, 1.0)
            final_score = combined_score * source_boost

            combined_results.append({
                **result,
                "score": final_score,
                "vector_score": vector_score,
                "bm25_score": normalized_bm25,
                "source_boost": source_boost
            })

        # Sort by combined score
        combined_results.sort(key=lambda x: x["score"], reverse=True)

        logger.info("Re-ranked results", original_count=len(results), top_k=top_k)
        return combined_results[:top_k]

