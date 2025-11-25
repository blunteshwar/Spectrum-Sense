"""Qdrant client wrapper for vector operations."""

from typing import List, Dict, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import structlog

logger = structlog.get_logger(__name__)


class QdrantClientWrapper:
    """Wrapper for Qdrant client operations."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "spectrum_docs",
        dimension: int = 768
    ):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.dimension = dimension
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure collection exists, create if not."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                logger.info("Creating collection", name=self.collection_name, dimension=self.dimension)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info("Collection created", name=self.collection_name)
            else:
                logger.info("Collection exists", name=self.collection_name)
        except Exception as e:
            logger.error("Error ensuring collection", error=str(e))
            raise

    def upsert_batch(self, vectors: List[List[float]], payloads: List[Dict[str, Any]]):
        """Upsert a batch of vectors with payloads."""
        if len(vectors) != len(payloads):
            raise ValueError("Vectors and payloads must have same length")

        points = []
        for i, (vector, payload) in enumerate(zip(vectors, payloads)):
            point_id = payload.get("id", i)
            # Convert string IDs to integers if needed (Qdrant supports both)
            if isinstance(point_id, str):
                # Use hash for string IDs
                point_id = abs(hash(point_id)) % (10 ** 18)

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            )

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.debug("Upserted batch", count=len(points))
        except Exception as e:
            logger.error("Error upserting batch", error=str(e))
            raise

    def search(
        self,
        query_vector: List[float],
        top_k: int = 50,
        score_threshold: Optional[float] = None,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        # Build filter if provided
        filter_condition = None
        if filter_dict:
            conditions = []
            for key, value in filter_dict.items():
                conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
            if conditions:
                filter_condition = Filter(must=conditions)

        try:
            # Use query_points API (newer qdrant-client)
            # query_points accepts a list[float] directly as the query parameter
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,  # Direct vector query
                limit=top_k,
                score_threshold=score_threshold,
                query_filter=filter_condition,
                with_payload=True,
                with_vectors=False
            )

            # Format results from query_points response
            formatted_results = []
            for point in results.points:
                formatted_results.append({
                    "id": point.id,
                    "score": point.score if hasattr(point, 'score') else 0.0,
                    "payload": point.payload if hasattr(point, 'payload') else {}
                })

            return formatted_results
        except Exception as e:
            logger.error("Error searching", error=str(e))
            raise

    def delete_collection(self):
        """Delete the collection (use with caution)."""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info("Collection deleted", name=self.collection_name)
        except Exception as e:
            logger.error("Error deleting collection", error=str(e))
            raise

    def get_collection_info(self) -> Dict[str, Any]:
        """Get collection information."""
        try:
            info = self.client.get_collection(self.collection_name)
            # Extract vector config safely
            vector_size = None
            distance_name = None
            if hasattr(info, 'config') and hasattr(info.config, 'params'):
                if hasattr(info.config.params, 'vectors'):
                    vectors = info.config.params.vectors
                    if hasattr(vectors, 'size'):
                        vector_size = vectors.size
                    if hasattr(vectors, 'distance'):
                        distance_name = vectors.distance.name if hasattr(vectors.distance, 'name') else str(vectors.distance)
            
            return {
                "name": self.collection_name,
                "points_count": info.points_count,
                "vectors_count": getattr(info, 'indexed_vectors_count', info.points_count),
                "config": {
                    "params": {
                        "vectors": {
                            "size": vector_size,
                            "distance": distance_name
                        }
                    }
                }
            }
        except Exception as e:
            logger.error("Error getting collection info", error=str(e))
            raise

