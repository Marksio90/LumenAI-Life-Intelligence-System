"""
RAG (Retrieval-Augmented Generation) System

Enterprise-grade RAG implementation with:
- Vector storage (Qdrant)
- Embeddings (OpenAI text-embedding-3-large)
- Intelligent chunking (recursive, semantic, sliding window)
- Hybrid search (BM25 + Vector)
- Reranking (Cohere)
- Redis caching
"""

from backend.services.rag.vector_store import (
    VectorStore,
    VectorDocument,
    CollectionConfig,
    get_vector_store
)
from backend.services.rag.embedding_service import (
    EmbeddingService,
    EmbeddingResult,
    get_embedding_service
)
from backend.services.rag.chunking_service import (
    ChunkingService,
    Chunk,
    Document,
    ChunkingStrategy,
    get_chunking_service
)
from backend.services.rag.rag_pipeline import (
    RAGPipeline,
    RAGResult,
    QueryExpansion,
    get_rag_pipeline
)

__all__ = [
    # Vector Store
    "VectorStore",
    "VectorDocument",
    "CollectionConfig",
    "get_vector_store",
    # Embeddings
    "EmbeddingService",
    "EmbeddingResult",
    "get_embedding_service",
    # Chunking
    "ChunkingService",
    "Chunk",
    "Document",
    "ChunkingStrategy",
    "get_chunking_service",
    # RAG Pipeline
    "RAGPipeline",
    "RAGResult",
    "QueryExpansion",
    "get_rag_pipeline",
]
