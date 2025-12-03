"""
LumenAI Gateway - Main FastAPI Application
WebSocket-enabled real-time AI assistant gateway
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys
from typing import Dict, List

# Add parent directory to path
sys.path.append('..')

from backend.shared.config.settings import settings
from backend.core.orchestrator import Orchestrator
from backend.core.memory import MemoryManager
from backend.services.mongodb_service import init_mongodb_service, get_mongodb_service
from backend.services.chromadb_service import init_chromadb_service, get_chromadb_service
from backend.services.embedding_service import init_embedding_service, get_embedding_service


# Connection Manager for WebSocket
class ConnectionManager:
    """Manages active WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected. Total connections: {len(self.active_connections)}")

    async def send_message(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)


# Initialize core components
manager = ConnectionManager()
orchestrator = None
memory_manager = None
mongodb_service = None
chromadb_service = None
embedding_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global orchestrator, memory_manager, mongodb_service, chromadb_service, embedding_service

    logger.info("🚀 Starting LumenAI...")

    # Initialize MongoDB
    try:
        mongodb_service = init_mongodb_service(
            connection_string=settings.MONGODB_URL,
            database_name=settings.MONGODB_DB_NAME
        )
        await mongodb_service.connect()
        logger.info("✅ MongoDB connected")
    except Exception as e:
        logger.warning(f"⚠️  MongoDB connection failed: {e}. Running without persistence.")
        mongodb_service = None

    # Initialize ChromaDB
    try:
        chromadb_service = init_chromadb_service(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT
        )
        await chromadb_service.connect()
        logger.info("✅ ChromaDB connected")
    except Exception as e:
        logger.warning(f"⚠️  ChromaDB connection failed: {e}. Running without vector search.")
        chromadb_service = None

    # Initialize Embedding Service
    try:
        if settings.OPENAI_API_KEY:
            embedding_service = init_embedding_service(
                api_key=settings.OPENAI_API_KEY
            )
            logger.info("✅ Embedding Service initialized")
        else:
            logger.warning("⚠️  No OpenAI API key - embeddings disabled")
            embedding_service = None
    except Exception as e:
        logger.warning(f"⚠️  Embedding Service failed: {e}")
        embedding_service = None

    # Initialize core systems
    memory_manager = MemoryManager()
    orchestrator = Orchestrator(memory_manager)

    logger.info("✅ LumenAI initialized successfully")

    yield

    # Cleanup
    logger.info("🛑 Shutting down LumenAI...")
    if mongodb_service:
        await mongodb_service.disconnect()
        logger.info("✅ MongoDB disconnected")
    if chromadb_service:
        await chromadb_service.disconnect()
        logger.info("✅ ChromaDB disconnected")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health Check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "🌟 Welcome to LumenAI - Your Life Intelligence System",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


# WebSocket endpoint for real-time chat
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time bidirectional communication
    """
    await manager.connect(websocket, user_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            logger.info(f"Received from {user_id}: {data}")

            # Extract message content
            message = data.get("message", "")
            message_type = data.get("type", "text")  # text, voice, image
            metadata = data.get("metadata", {})

            # Send typing indicator
            await manager.send_message(user_id, {
                "type": "status",
                "status": "typing"
            })

            # Process through orchestrator
            response = await orchestrator.process_message(
                user_id=user_id,
                message=message,
                message_type=message_type,
                metadata=metadata
            )

            # Send response back to client
            await manager.send_message(user_id, {
                "type": "message",
                "content": response["content"],
                "agent": response.get("agent", "unknown"),
                "metadata": response.get("metadata", {})
            })

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        logger.info(f"Client {user_id} disconnected")
    except Exception as e:
        logger.error(f"Error in WebSocket for {user_id}: {e}")
        manager.disconnect(user_id)


# REST API Endpoints

@app.post("/api/v1/chat")
async def chat(request: dict):
    """
    REST endpoint for chat (alternative to WebSocket)
    """
    try:
        user_id = request.get("user_id")
        message = request.get("message")
        message_type = request.get("type", "text")

        if not user_id or not message:
            raise HTTPException(status_code=400, detail="user_id and message are required")

        response = await orchestrator.process_message(
            user_id=user_id,
            message=message,
            message_type=message_type
        )

        return JSONResponse(content=response)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/user/{user_id}/history")
async def get_user_history(user_id: str, limit: int = 50):
    """Get user's conversation history"""
    try:
        history = await memory_manager.get_user_history(user_id, limit=limit)
        return {"user_id": user_id, "history": history}
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/user/{user_id}/memory")
async def clear_user_memory(user_id: str):
    """Clear user's memory (privacy feature)"""
    try:
        await memory_manager.clear_user_memory(user_id)
        return {"status": "success", "message": f"Memory cleared for user {user_id}"}
    except Exception as e:
        logger.error(f"Error clearing memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/stats/costs")
async def get_cost_stats():
    """Get LLM API cost statistics"""
    try:
        from backend.core.cost_tracker import cost_tracker
        stats = cost_tracker.get_stats()

        # Add estimated monthly cost
        if stats["total_requests"] > 0:
            stats["estimated_monthly_cost"] = cost_tracker.estimate_monthly_cost(
                requests_per_day=100
            )

        return {
            "status": "success",
            "data": stats,
            "message": f"💰 Total cost: ${stats['total_cost']:.4f}"
        }
    except Exception as e:
        logger.error(f"Error fetching cost stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NEW: MongoDB-powered endpoints
# ============================================================================

@app.get("/api/v1/user/{user_id}/conversations")
async def get_user_conversations(user_id: str, limit: int = 20, skip: int = 0):
    """
    Get user's conversations with MongoDB persistence

    NEW FEATURE: Conversations now persist across restarts! 🎉
    """
    try:
        db = get_mongodb_service()
        conversations = await db.get_user_conversations(user_id, limit=limit, skip=skip)

        return {
            "status": "success",
            "user_id": user_id,
            "total": len(conversations),
            "conversations": [
                {
                    "conversation_id": conv.conversation_id,
                    "title": conv.title,
                    "started_at": conv.started_at.isoformat(),
                    "last_message_at": conv.last_message_at.isoformat(),
                    "message_count": conv.message_count,
                    "agents_used": conv.agents_used,
                    "status": conv.status
                }
                for conv in conversations
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/conversation/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str, limit: int = 100):
    """
    Get all messages from a conversation

    NEW FEATURE: Full conversation history from MongoDB! 💬
    """
    try:
        db = get_mongodb_service()
        messages = await db.get_conversation_messages(conversation_id, limit=limit)

        return {
            "status": "success",
            "conversation_id": conversation_id,
            "total": len(messages),
            "messages": [
                {
                    "message_id": msg.message_id,
                    "role": msg.role,
                    "content": msg.content,
                    "agent": msg.agent,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": {
                        "tokens": msg.metadata.tokens,
                        "cost": msg.metadata.cost,
                        "model": msg.metadata.model
                    }
                }
                for msg in messages
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/user/{user_id}/mood/history")
async def get_mood_history(user_id: str, days: int = 7):
    """
    Get user's mood history

    NEW FEATURE: Mood tracking with MongoDB! 😊
    """
    try:
        mood_history = await memory_manager.get_mood_history(user_id, days=days)

        return {
            "status": "success",
            "user_id": user_id,
            "days": days,
            "total_entries": len(mood_history),
            "entries": mood_history
        }
    except Exception as e:
        logger.error(f"Error fetching mood history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/user/{user_id}/mood/stats")
async def get_mood_stats(user_id: str, days: int = 30):
    """
    Get mood statistics and insights

    NEW FEATURE: Analyze mood patterns! 📊
    """
    try:
        stats = await memory_manager.get_mood_statistics(user_id, days=days)

        return {
            "status": "success",
            "user_id": user_id,
            "period_days": days,
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"Error fetching mood stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/db/health")
async def database_health():
    """Check MongoDB connection status"""
    try:
        db = get_mongodb_service()
        is_healthy = await db.health_check()

        if is_healthy:
            stats = await db.get_database_stats()
            return {
                "status": "healthy",
                "database": stats.get("database"),
                "collections": stats.get("collections"),
                "total_documents": stats.get("objects")
            }
        else:
            return {
                "status": "unhealthy",
                "message": "MongoDB connection failed"
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )

# ============================================================================
# SEMANTIC SEARCH - ChromaDB-powered endpoints
# ============================================================================

@app.post("/api/v1/search/conversations")
async def search_conversations(user_id: str, query: str, n_results: int = 10):
    """
    Semantic search for conversations using ChromaDB.

    Example:
        POST /api/v1/search/conversations
        Body: {"user_id": "user_123", "query": "jak radzić sobie ze stresem?", "n_results": 5}

    Response:
        {
            "status": "success",
            "query": "jak radzić sobie ze stresem?",
            "total": 5,
            "results": [
                {
                    "content": "...",
                    "similarity": 0.92,
                    "metadata": {...}
                }
            ]
        }
    """
    try:
        results = await memory_manager.search_similar_conversations(
            user_id=user_id,
            query=query,
            n_results=n_results
        )

        return {
            "status": "success",
            "query": query,
            "user_id": user_id,
            "total": len(results),
            "results": results
        }

    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/chromadb/health")
async def chromadb_health():
    """Check ChromaDB connection status and stats"""
    try:
        chromadb = get_chromadb_service()
        embedding_service = get_embedding_service()

        chromadb_status = await chromadb.health_check() if chromadb else False
        chromadb_stats = chromadb.get_stats() if chromadb else {}

        embedding_stats = embedding_service.get_cache_stats() if embedding_service else {}

        return {
            "chromadb": {
                "status": "healthy" if chromadb_status else "unavailable",
                **chromadb_stats
            },
            "embeddings": {
                "status": "available" if embedding_service else "unavailable",
                **embedding_stats
            }
        }

    except Exception as e:
        logger.error(f"ChromaDB health check failed: {e}")
        return {
            "chromadb": {"status": "error", "message": str(e)},
            "embeddings": {"status": "unknown"}
        }


@app.post("/api/v1/embeddings/generate")
async def generate_embedding(text: str):
    """
    Generate embedding for text (utility endpoint for testing).

    Example:
        POST /api/v1/embeddings/generate
        Body: {"text": "Hello world"}

    Response:
        {
            "status": "success",
            "text": "Hello world",
            "embedding": [0.123, -0.456, ...],  # 1536 dimensions
            "dimensions": 1536
        }
    """
    try:
        embedding_service = get_embedding_service()
        if not embedding_service:
            raise HTTPException(status_code=503, detail="Embedding service not available")

        embedding = await embedding_service.generate(text)

        return {
            "status": "success",
            "text": text,
            "embedding": embedding,
            "dimensions": len(embedding)
        }

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

