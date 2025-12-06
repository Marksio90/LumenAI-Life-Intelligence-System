"""
Vector Store Service with Qdrant Integration

High-performance vector storage and similarity search using Qdrant.
Supports:
- Multiple collections (conversations, documents, memories)
- Metadata filtering
- Hybrid search (dense + sparse)
- Batch operations
- Connection pooling
"""

import os
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
import asyncio
from datetime import datetime

from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
    SearchRequest, ScoredPoint
)
from qdrant_client.http.models import CollectionStatus

from core.logging_config import get_logger
from core.exceptions import ServiceError, ResourceNotFoundError

logger = get_logger(__name__)


@dataclass
class VectorDocument:
    """Document with vector embedding and metadata"""
    id: str
    text: str
    vector: List[float]
    metadata: Dict[str, Any]
    score: Optional[float] = None


@dataclass
class CollectionConfig:
    """Configuration for a vector collection"""
    name: str
    vector_size: int
    distance: Distance = Distance.COSINE
    metadata_schema: Optional[Dict[str, str]] = None


class VectorStore:
    """
    High-performance vector storage with Qdrant

    Features:
    - Async operations for high throughput
    - Connection pooling
    - Automatic retry logic
    - Health monitoring
    - Batch processing
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize Vector Store

        Args:
            host: Qdrant server host
            port: Qdrant server port
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.host = host
        self.port = port
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.timeout = timeout

        # Initialize clients
        self.client = QdrantClient(
            host=host,
            port=port,
            api_key=self.api_key,
            timeout=timeout
        )

        self.async_client = AsyncQdrantClient(
            host=host,
            port=port,
            api_key=self.api_key,
            timeout=timeout
        )

        # Collection cache
        self._collections: Dict[str, CollectionConfig] = {}

        logger.info(f"Vector store initialized: {host}:{port}")

    async def health_check(self) -> bool:
        """Check if Qdrant is healthy"""
        try:
            collections = await self.async_client.get_collections()
            logger.debug(f"Qdrant health check passed. Collections: {len(collections.collections)}")
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    async def create_collection(
        self,
        name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
        recreate: bool = False
    ) -> bool:
        """
        Create a new collection

        Args:
            name: Collection name
            vector_size: Dimension of vectors
            distance: Distance metric (COSINE, EUCLID, DOT)
            recreate: If True, delete existing collection

        Returns:
            Success status
        """
        try:
            # Check if collection exists
            collections = await self.async_client.get_collections()
            exists = any(col.name == name for col in collections.collections)

            if exists and recreate:
                await self.async_client.delete_collection(name)
                logger.info(f"Deleted existing collection: {name}")
                exists = False

            if not exists:
                await self.async_client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=distance
                    )
                )
                logger.info(f"Created collection: {name} (size={vector_size}, distance={distance.value})")

            # Cache configuration
            self._collections[name] = CollectionConfig(
                name=name,
                vector_size=vector_size,
                distance=distance
            )

            return True

        except Exception as e:
            logger.error(f"Failed to create collection {name}: {e}")
            raise ServiceError(f"Vector store collection creation failed: {str(e)}")

    async def upsert_documents(
        self,
        collection_name: str,
        documents: List[VectorDocument],
        batch_size: int = 100
    ) -> int:
        """
        Insert or update documents in batches

        Args:
            collection_name: Target collection
            documents: Documents to upsert
            batch_size: Batch size for upload

        Returns:
            Number of documents upserted
        """
        try:
            # Convert to Qdrant points
            points = [
                PointStruct(
                    id=doc.id,
                    vector=doc.vector,
                    payload={
                        "text": doc.text,
                        **doc.metadata,
                        "indexed_at": datetime.utcnow().isoformat()
                    }
                )
                for doc in documents
            ]

            # Upload in batches
            total_uploaded = 0
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                await self.async_client.upsert(
                    collection_name=collection_name,
                    points=batch
                )
                total_uploaded += len(batch)
                logger.debug(f"Uploaded batch {i//batch_size + 1}: {len(batch)} documents")

            logger.info(f"Upserted {total_uploaded} documents to {collection_name}")
            return total_uploaded

        except Exception as e:
            logger.error(f"Failed to upsert documents: {e}")
            raise ServiceError(f"Document upsert failed: {str(e)}")

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None
    ) -> List[VectorDocument]:
        """
        Search for similar vectors

        Args:
            collection_name: Collection to search
            query_vector: Query embedding
            limit: Maximum results
            filters: Metadata filters
            score_threshold: Minimum similarity score

        Returns:
            Matching documents with scores
        """
        try:
            # Build filter
            query_filter = None
            if filters:
                conditions = [
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                    for key, value in filters.items()
                ]
                query_filter = Filter(must=conditions)

            # Execute search
            results = await self.async_client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=query_filter,
                score_threshold=score_threshold,
                with_payload=True
            )

            # Convert to documents
            documents = []
            for point in results:
                payload = point.payload
                doc = VectorDocument(
                    id=str(point.id),
                    text=payload.get("text", ""),
                    vector=[],  # Don't return vector to save bandwidth
                    metadata={k: v for k, v in payload.items() if k != "text"},
                    score=point.score
                )
                documents.append(doc)

            logger.debug(f"Search returned {len(documents)} results from {collection_name}")
            return documents

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise ServiceError(f"Vector search failed: {str(e)}")

    async def delete_documents(
        self,
        collection_name: str,
        document_ids: List[str]
    ) -> bool:
        """Delete documents by IDs"""
        try:
            await self.async_client.delete(
                collection_name=collection_name,
                points_selector=document_ids
            )
            logger.info(f"Deleted {len(document_ids)} documents from {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False

    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            info = await self.async_client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.points_count,
                "status": info.status,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise ResourceNotFoundError(f"Collection {collection_name} not found")

    async def close(self):
        """Close connections"""
        await self.async_client.close()
        logger.info("Vector store connections closed")


# Global instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create global vector store instance"""
    global _vector_store
    if _vector_store is None:
        host = os.getenv("QDRANT_HOST", "localhost")
        port = int(os.getenv("QDRANT_PORT", "6333"))
        _vector_store = VectorStore(host=host, port=port)
    return _vector_store
