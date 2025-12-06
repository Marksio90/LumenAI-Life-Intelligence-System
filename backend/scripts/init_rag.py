#!/usr/bin/env python3
"""
RAG System Initialization Script

Initializes the RAG system with:
- Qdrant collections
- Sample data (optional)
- Health checks
- Configuration validation

Usage:
    python backend/scripts/init_rag.py
    python backend/scripts/init_rag.py --with-samples
    python backend/scripts/init_rag.py --reset  # WARNING: Deletes all data
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.rag import (
    get_vector_store,
    get_embedding_service,
    get_rag_pipeline,
    Document
)
from core.logging_config import get_logger

logger = get_logger(__name__)


async def check_services():
    """Check if all required services are available"""
    logger.info("🔍 Checking RAG services...")

    # Check Qdrant
    try:
        vector_store = get_vector_store()
        is_healthy = await vector_store.health_check()
        if is_healthy:
            logger.info("✅ Qdrant is healthy")
        else:
            logger.error("❌ Qdrant health check failed")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to connect to Qdrant: {e}")
        return False

    # Check Embedding Service (requires OpenAI API key)
    try:
        embedding_service = get_embedding_service()
        logger.info(f"✅ Embedding service initialized (model={embedding_service.model}, dim={embedding_service.embedding_dim})")
    except Exception as e:
        logger.error(f"❌ Failed to initialize embedding service: {e}")
        logger.error("💡 Make sure OPENAI_API_KEY is set in environment")
        return False

    # Check Redis (optional for caching)
    try:
        stats = await embedding_service.get_stats()
        logger.info(f"✅ Redis cache available (hit rate: {stats['cache_hit_rate']})")
    except Exception as e:
        logger.warning(f"⚠️  Redis not available (embeddings will not be cached): {e}")

    return True


async def initialize_collections(reset: bool = False):
    """Initialize Qdrant collections"""
    logger.info("📚 Initializing collections...")

    rag_pipeline = get_rag_pipeline()

    if reset:
        logger.warning("⚠️  RESET MODE: Clearing existing collections...")
        await rag_pipeline.clear_index()

    # Initialize main collection
    await rag_pipeline.initialize_collection()

    logger.info("✅ Collections initialized")


async def load_sample_data():
    """Load sample data for testing"""
    logger.info("📝 Loading sample data...")

    rag_pipeline = get_rag_pipeline()

    # Sample documents
    samples = [
        Document(
            id="sample_1",
            text="LumenAI to zaawansowany system AI do zarządzania życiem codziennym. "
                 "Pomaga w organizacji zadań, analizie nastroju i poprawie produktywności.",
            metadata={
                "type": "about",
                "category": "platform",
                "language": "pl"
            }
        ),
        Document(
            id="sample_2",
            text="System RAG (Retrieval-Augmented Generation) łączy wyszukiwanie semantyczne "
                 "z generowaniem tekstu. Używa Qdrant do przechowywania embeddings i Cohere do rerankingu.",
            metadata={
                "type": "technical",
                "category": "rag",
                "language": "pl"
            }
        ),
        Document(
            id="sample_3",
            text="Hybrid search combines BM25 keyword matching with vector similarity search. "
                 "This provides better results than using either method alone.",
            metadata={
                "type": "technical",
                "category": "search",
                "language": "en"
            }
        ),
        Document(
            id="sample_4",
            text="Cohere reranking improves search results by re-scoring documents based on semantic relevance. "
                 "It's the final step in our multi-stage retrieval pipeline.",
            metadata={
                "type": "technical",
                "category": "reranking",
                "language": "en"
            }
        ),
        Document(
            id="sample_5",
            text="Zarządzanie stresem to kluczowy element zdrowia psychicznego. "
                 "Techniki takie jak medytacja, ćwiczenia oddechowe i regularna aktywność fizyczna mogą znacząco pomóc.",
            metadata={
                "type": "wellness",
                "category": "mental_health",
                "language": "pl"
            }
        )
    ]

    # Index samples
    for doc in samples:
        chunks_count = await rag_pipeline.index_document(doc, strategy="recursive")
        logger.info(f"✅ Indexed: {doc.id} ({chunks_count} chunks)")

    logger.info(f"✅ Loaded {len(samples)} sample documents")


async def test_search():
    """Test search functionality"""
    logger.info("🔍 Testing search...")

    rag_pipeline = get_rag_pipeline()

    # Test queries
    test_queries = [
        ("Co to jest LumenAI?", "pl"),
        ("How does hybrid search work?", "en"),
        ("stress management techniques", "en")
    ]

    for query, lang in test_queries:
        logger.info(f"\n📋 Query: '{query}' (lang={lang})")

        result = await rag_pipeline.retrieve(
            query=query,
            top_k=3,
            use_hybrid=True,
            use_rerank=True
        )

        logger.info(f"⏱️  Retrieved in {result.retrieval_time_ms:.2f}ms")
        logger.info(f"📊 Strategy: {result.strategy}")
        logger.info(f"📄 Results: {len(result.documents)}")

        for i, doc in enumerate(result.documents, 1):
            logger.info(f"  {i}. Score: {doc.score:.4f} | {doc.text[:100]}...")

    logger.info("✅ Search test completed")


async def show_stats():
    """Show system statistics"""
    logger.info("\n📊 System Statistics:")

    rag_pipeline = get_rag_pipeline()
    stats = await rag_pipeline.get_stats()

    logger.info(f"  Total queries: {stats['total_queries']}")
    logger.info(f"  Avg retrieval time: {stats['avg_retrieval_time_ms']:.2f}ms")
    logger.info(f"  BM25 documents: {stats['bm25_documents']}")

    if 'collection' in stats:
        coll = stats['collection']
        logger.info(f"  Collection: {coll.get('name', 'N/A')}")
        logger.info(f"  Vectors: {coll.get('vectors_count', 0)}")

    if 'embedding' in stats:
        emb = stats['embedding']
        logger.info(f"  Embedding cache hit rate: {emb.get('cache_hit_rate', 'N/A')}")
        logger.info(f"  Total cost: ${emb.get('total_cost', 0):.4f}")


async def main():
    parser = argparse.ArgumentParser(description="Initialize RAG system")
    parser.add_argument("--with-samples", action="store_true", help="Load sample data")
    parser.add_argument("--reset", action="store_true", help="Reset all data (WARNING: deletes everything)")
    parser.add_argument("--test", action="store_true", help="Run search tests")
    parser.add_argument("--stats", action="store_true", help="Show statistics")

    args = parser.parse_args()

    logger.info("🚀 LumenAI RAG System Initialization\n")

    # Step 1: Check services
    if not await check_services():
        logger.error("❌ Service check failed. Please ensure Qdrant and Redis are running:")
        logger.error("   docker-compose -f docker-compose.rag.yml up -d")
        sys.exit(1)

    logger.info("")

    # Step 2: Initialize collections
    await initialize_collections(reset=args.reset)
    logger.info("")

    # Step 3: Load samples (if requested)
    if args.with_samples:
        await load_sample_data()
        logger.info("")

    # Step 4: Run tests (if requested)
    if args.test:
        if not args.with_samples:
            logger.warning("⚠️  No sample data loaded. Run with --with-samples first.")
        else:
            await test_search()
        logger.info("")

    # Step 5: Show stats (if requested)
    if args.stats:
        await show_stats()
        logger.info("")

    logger.info("✅ RAG system initialization complete!")
    logger.info("\n💡 Quick start:")
    logger.info("   1. Make sure services are running: docker-compose -f docker-compose.rag.yml up -d")
    logger.info("   2. Start FastAPI backend: uvicorn backend.gateway.main:app --reload")
    logger.info("   3. Use RAG in your code:")
    logger.info("      from services.rag import get_rag_pipeline")
    logger.info("      rag = get_rag_pipeline()")
    logger.info("      result = await rag.retrieve(query='your query', top_k=5)")


if __name__ == "__main__":
    asyncio.run(main())
