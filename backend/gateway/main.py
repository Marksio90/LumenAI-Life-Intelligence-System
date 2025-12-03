"""
LumenAI Gateway - Main FastAPI Application
WebSocket-enabled real-time AI assistant gateway
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys
from typing import Dict, List, Optional
import base64

# Add parent directory to path
sys.path.append('..')

from backend.shared.config.settings import settings
from backend.core.orchestrator import Orchestrator
from backend.core.memory import MemoryManager
from backend.services.mongodb_service import init_mongodb_service, get_mongodb_service
from backend.services.chromadb_service import init_chromadb_service, get_chromadb_service
from backend.services.embedding_service import init_embedding_service, get_embedding_service
from backend.services.analytics_service import init_analytics_service, get_analytics_service
from backend.services.notification_service import init_notification_service, get_notification_service
from backend.ml.feature_engineering import FeatureEngineer
from backend.ml.training_service import init_training_service, get_training_service


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
analytics_service = None
notification_service = None
feature_engineer = None
training_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global orchestrator, memory_manager, mongodb_service, chromadb_service, embedding_service, analytics_service, notification_service, feature_engineer, training_service

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

    # Initialize Analytics Service (requires all other services)
    try:
        if chromadb_service and embedding_service:
            analytics_service = init_analytics_service(
                llm_engine=orchestrator.llm_engine,
                memory_manager=memory_manager,
                chromadb_service=chromadb_service,
                embedding_service=embedding_service
            )
            logger.info("✅ Analytics Service initialized")
        else:
            logger.warning("⚠️  Analytics Service disabled (requires ChromaDB + Embeddings)")
            analytics_service = None
    except Exception as e:
        logger.warning(f"⚠️  Analytics Service failed: {e}")
        analytics_service = None

    # Initialize ML Services (Feature Engineering + Training)
    try:
        feature_engineer = FeatureEngineer(
            memory_manager=memory_manager,
            embedding_service=embedding_service
        )
        logger.info("✅ Feature Engineer initialized")

        training_service = init_training_service(
            memory_manager=memory_manager,
            feature_engineer=feature_engineer,
            models_dir="backend/ml/models"
        )
        logger.info("✅ ML Training Service initialized")
    except Exception as e:
        logger.warning(f"⚠️  ML Services failed: {e}. Running without ML capabilities.")
        feature_engineer = None
        training_service = None

    # Initialize Notification Service
    try:
        notification_service = init_notification_service(
            memory_manager=memory_manager,
            training_service=training_service,
            analytics_service=analytics_service
        )
        logger.info("✅ Notification Service initialized")
    except Exception as e:
        logger.warning(f"⚠️  Notification Service failed: {e}. Running without notifications.")
        notification_service = None

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
    WebSocket endpoint for real-time bidirectional communication + notifications
    """
    await manager.connect(websocket, user_id)

    # Register notification callback for real-time push
    if notification_service:
        async def notification_callback(notification):
            """Send notification through WebSocket"""
            await manager.send_message(user_id, {
                "type": "notification",
                "notification": notification.to_dict()
            })
        notification_service.register_callback(user_id, notification_callback)

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

            # Check for smart notifications after message processing
            if notification_service:
                # Check mood-based notifications if mood was tracked
                if metadata.get("mood"):
                    await notification_service.detect_mood_drop(user_id, metadata["mood"])
                    await notification_service.detect_mood_improvement(user_id, metadata["mood"])

                # Check ML predictions
                await notification_service.check_ml_predictions(user_id, message)

    except WebSocketDisconnect:
        if notification_service:
            notification_service.unregister_callback(user_id)
        manager.disconnect(user_id)
        logger.info(f"Client {user_id} disconnected")
    except Exception as e:
        logger.error(f"Error in WebSocket for {user_id}: {e}")
        if notification_service:
            notification_service.unregister_callback(user_id)
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


# ============================================================================
# ANALYTICS - Advanced Conversation Analysis
# ============================================================================

@app.post("/api/v1/analytics/conversation/{conversation_id}/summary")
async def summarize_conversation(conversation_id: str, max_length: int = 200):
    """
    Generate automatic conversation summary using LLM.

    Example:
        POST /api/v1/analytics/conversation/conv_123/summary?max_length=150

    Response:
        {
            "status": "success",
            "conversation_id": "conv_123",
            "summary": {
                "summary": "Użytkownik rozmawiał o stresie w pracy...",
                "key_topics": ["praca", "stres", "zarządzanie czasem"],
                "sentiment": "neutral",
                "action_items": ["Spróbuj techniki oddechowej..."],
                "insights": ["Wzrost stresu w ostatnich dniach"]
            }
        }
    """
    try:
        analytics = get_analytics_service()
        if not analytics:
            raise HTTPException(status_code=503, detail="Analytics service not available")

        summary = await analytics.summarize_conversation(
            conversation_id=conversation_id,
            max_length=max_length
        )

        return {
            "status": "success",
            "conversation_id": conversation_id,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Conversation summarization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/user/{user_id}/clusters")
async def get_topic_clusters(user_id: str, n_clusters: int = 5, min_conversations: int = 3):
    """
    Group user's conversations by topics using K-means clustering.

    Example:
        GET /api/v1/analytics/user/user_123/clusters?n_clusters=5

    Response:
        {
            "status": "success",
            "user_id": "user_123",
            "total_clusters": 3,
            "clusters": [
                {
                    "cluster_id": 0,
                    "label": "Praca i kariera",
                    "size": 12,
                    "sample_topics": ["rozmowa kwalifikacyjna", "zarządzanie czasem"]
                },
                ...
            ]
        }
    """
    try:
        analytics = get_analytics_service()
        if not analytics:
            raise HTTPException(status_code=503, detail="Analytics service not available")

        clusters = await analytics.cluster_conversations_by_topic(
            user_id=user_id,
            n_clusters=n_clusters,
            min_conversations=min_conversations
        )

        return {
            "status": "success",
            "user_id": user_id,
            "total_clusters": len(clusters["clusters"]),
            "clusters": clusters["clusters"]
        }

    except Exception as e:
        logger.error(f"Topic clustering failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/user/{user_id}/trends")
async def get_mood_trends(user_id: str, days: int = 30):
    """
    Analyze mood trends over time with statistical analysis.

    Example:
        GET /api/v1/analytics/user/user_123/trends?days=30

    Response:
        {
            "status": "success",
            "user_id": "user_123",
            "period": "30 days",
            "trends": {
                "trend": "improving",  # improving/declining/stable
                "slope": 0.15,
                "statistics": {
                    "average_intensity": 7.2,
                    "volatility": "moderate",
                    "most_common_mood": "happy"
                },
                "data_points": [...],
                "insights": ["Mood improving over last 2 weeks", ...]
            }
        }
    """
    try:
        analytics = get_analytics_service()
        if not analytics:
            raise HTTPException(status_code=503, detail="Analytics service not available")

        trends = await analytics.analyze_mood_trends(
            user_id=user_id,
            days=days
        )

        return {
            "status": "success",
            "user_id": user_id,
            "period": f"{days} days",
            "trends": trends
        }

    except Exception as e:
        logger.error(f"Trend analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/user/{user_id}/recommendations")
async def get_recommendations(user_id: str, n_recommendations: int = 5):
    """
    Get personalized recommendations based on conversation patterns.

    Example:
        GET /api/v1/analytics/user/user_123/recommendations?n_recommendations=5

    Response:
        {
            "status": "success",
            "user_id": "user_123",
            "total": 5,
            "recommendations": [
                {
                    "type": "topic",
                    "title": "Eksploruj techniki mindfulness",
                    "description": "Na podstawie twoich rozmów o stresie...",
                    "confidence": 0.85,
                    "source": "topic_clustering"
                },
                {
                    "type": "mood",
                    "title": "Rozważ regularne ćwiczenia",
                    "description": "Twój nastrój poprawia się w dni, gdy wspominasz o aktywności",
                    "confidence": 0.72,
                    "source": "mood_trends"
                },
                ...
            ]
        }
    """
    try:
        analytics = get_analytics_service()
        if not analytics:
            raise HTTPException(status_code=503, detail="Analytics service not available")

        recommendations = await analytics.get_recommendations(
            user_id=user_id,
            n_recommendations=n_recommendations
        )

        return {
            "status": "success",
            "user_id": user_id,
            "total": len(recommendations["recommendations"]),
            "recommendations": recommendations["recommendations"]
        }

    except Exception as e:
        logger.error(f"Recommendations generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/health")
async def analytics_health():
    """Check Analytics Service status and dependencies"""
    try:
        analytics = get_analytics_service()

        if not analytics:
            return {
                "status": "unavailable",
                "message": "Analytics service not initialized (requires ChromaDB + Embeddings)"
            }

        # Check all dependencies
        chromadb_ok = await analytics.chromadb.health_check() if analytics.chromadb else False
        embedding_ok = analytics.embeddings is not None

        return {
            "status": "healthy" if (chromadb_ok and embedding_ok) else "degraded",
            "dependencies": {
                "chromadb": "healthy" if chromadb_ok else "unavailable",
                "embeddings": "available" if embedding_ok else "unavailable",
                "llm_engine": "available" if analytics.llm else "unavailable",
                "memory_manager": "available" if analytics.memory else "unavailable"
            },
            "features": {
                "summarization": analytics.llm is not None,
                "clustering": chromadb_ok and embedding_ok,
                "trends": True,  # Only needs MongoDB
                "recommendations": chromadb_ok and embedding_ok
            }
        }

    except Exception as e:
        logger.error(f"Analytics health check failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================================
# FILE UPLOAD - Image and Audio Processing
# ============================================================================

@app.post("/api/v1/upload/image")
async def upload_image(
    user_id: str = Form(...),
    message: str = Form(""),
    file: UploadFile = File(...)
):
    """
    Upload and process image with Vision Agent.

    Supports OCR, object detection, scene description.

    Example:
        POST /api/v1/upload/image
        Form data:
            - user_id: "user_123"
            - message: "Co jest na tym zdjęciu?"
            - file: image.jpg

    Response:
        {
            "status": "success",
            "response": "🔍 **Analiza obrazu:**\n\n...",
            "agent": "Vision"
        }
    """
    try:
        # Validate file type
        content_type = file.content_type
        if not content_type or not content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Read image data
        image_bytes = await file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # Add data URL prefix
        mime_type = content_type
        image_data = f"data:{mime_type};base64,{image_base64}"

        # Process with orchestrator
        response = await orchestrator.process_message(
            user_id=user_id,
            message=message or "Przeanalizuj to zdjęcie",
            message_type="image",
            metadata={
                "image": image_data,
                "filename": file.filename,
                "content_type": content_type
            }
        )

        return {
            "status": "success",
            "response": response["content"],
            "agent": response.get("agent", "unknown"),
            "metadata": response.get("metadata", {})
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/upload/audio")
async def upload_audio(
    user_id: str = Form(...),
    message: str = Form(""),
    language: str = Form("pl"),
    file: UploadFile = File(...)
):
    """
    Upload and transcribe audio with Speech Agent.

    Supports multiple audio formats (mp3, wav, m4a, webm, etc.)

    Example:
        POST /api/v1/upload/audio
        Form data:
            - user_id: "user_123"
            - message: "Przetranskrybuj to nagranie"
            - language: "pl"
            - file: recording.mp3

    Response:
        {
            "status": "success",
            "response": "🎤 **Transkrypcja:**\n\n...",
            "agent": "Speech",
            "transcription": "..."
        }
    """
    try:
        # Validate file type
        content_type = file.content_type
        if not content_type or not content_type.startswith('audio/'):
            # Also accept video formats (some browsers send audio as video/webm)
            if not content_type.startswith('video/'):
                raise HTTPException(status_code=400, detail="File must be audio")

        # Read audio data
        audio_bytes = await file.read()
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        # Get file extension
        filename = file.filename or "audio.mp3"
        audio_format = filename.split('.')[-1].lower()

        # Process with orchestrator
        response = await orchestrator.process_message(
            user_id=user_id,
            message=message or "Transkrybuj to nagranie",
            message_type="audio",
            metadata={
                "audio": audio_base64,
                "audio_format": audio_format,
                "filename": filename,
                "language": language,
                "content_type": content_type
            }
        )

        return {
            "status": "success",
            "response": response["content"],
            "agent": response.get("agent", "unknown"),
            "metadata": response.get("metadata", {})
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/tts")
async def text_to_speech(
    user_id: str,
    text: str,
    voice: str = "alloy",
    model: str = "tts-1"
):
    """
    Convert text to speech using OpenAI TTS.

    Available voices: alloy, echo, fable, onyx, nova, shimmer
    Models: tts-1 (fast), tts-1-hd (high quality)

    Example:
        POST /api/v1/tts
        Body: {
            "user_id": "user_123",
            "text": "Witaj w LumenAI!",
            "voice": "alloy",
            "model": "tts-1"
        }

    Response:
        {
            "status": "success",
            "audio_base64": "...",
            "audio_format": "mp3",
            "voice": "alloy"
        }
    """
    try:
        # Process with orchestrator (Speech Agent will handle TTS)
        response = await orchestrator.process_message(
            user_id=user_id,
            message=f"Przeczytaj: {text}",
            message_type="tts",
            metadata={
                "voice": voice,
                "tts_model": model
            }
        )

        # Check if response contains audio
        if isinstance(response.get("content"), dict) and "audio_base64" in response["content"]:
            return {
                "status": "success",
                **response["content"]
            }

        return {
            "status": "success",
            "message": response.get("content", "TTS generation completed")
        }

    except Exception as e:
        logger.error(f"TTS failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MACHINE LEARNING - Personalized ML Models
# ============================================================================

@app.post("/api/v1/ml/train/mood-predictor/{user_id}")
async def train_mood_predictor(user_id: str, min_samples: int = 50):
    """
    Trenuje personalizowany model przewidywania nastroju dla użytkownika.

    Model uczy się na historycznych danych użytkownika i potrafi przewidzieć
    przyszły nastrój na podstawie kontekstu rozmowy.

    Example:
        POST /api/v1/ml/train/mood-predictor/user_123?min_samples=50

    Response:
        {
            "success": true,
            "model_type": "mood_predictor",
            "user_id": "user_123",
            "n_samples": 150,
            "metrics": {
                "test_rmse": 1.23,
                "test_mae": 0.98
            },
            "top_features": [...]
        }
    """
    try:
        training = get_training_service()
        if not training:
            raise HTTPException(status_code=503, detail="ML Training Service not available")

        result = await training.train_mood_predictor(
            user_id=user_id,
            min_samples=min_samples
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Training failed"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mood predictor training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ml/train/behavior-profiler/{user_id}")
async def train_behavior_profiler(user_id: str, min_samples: int = 50):
    """
    Trenuje personalizowany model profilowania zachowań użytkownika.

    Model klasyfikuje zachowania użytkownika (positive/neutral/negative)
    na podstawie wzorców w danych historycznych.

    Example:
        POST /api/v1/ml/train/behavior-profiler/user_123?min_samples=50

    Response:
        {
            "success": true,
            "model_type": "behavior_profiler",
            "user_id": "user_123",
            "n_samples": 150,
            "metrics": {
                "test_accuracy": 0.85,
                "test_f1": 0.82
            },
            "class_distribution": {...}
        }
    """
    try:
        training = get_training_service()
        if not training:
            raise HTTPException(status_code=503, detail="ML Training Service not available")

        result = await training.train_behavior_profiler(
            user_id=user_id,
            min_samples=min_samples
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Training failed"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Behavior profiler training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ml/predict/mood")
async def predict_mood(user_id: str, message: str):
    """
    Przewiduje nastrój użytkownika na podstawie aktualnego kontekstu.

    Wymaga wcześniej wytrenowanego modelu dla tego użytkownika.

    Example:
        POST /api/v1/ml/predict/mood
        Body: {"user_id": "user_123", "message": "Czuję się dzisiaj świetnie!"}

    Response:
        {
            "status": "success",
            "user_id": "user_123",
            "prediction": {
                "predicted_mood": 8.2,
                "confidence": 0.75,
                "timestamp": "2025-12-03T12:00:00"
            }
        }
    """
    try:
        training = get_training_service()
        if not training:
            raise HTTPException(status_code=503, detail="ML Training Service not available")

        prediction = await training.predict_mood(user_id=user_id, message=message)

        if prediction is None:
            raise HTTPException(
                status_code=404,
                detail=f"No trained mood predictor model found for user {user_id}. Please train first."
            )

        return {
            "status": "success",
            "user_id": user_id,
            "prediction": prediction
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mood prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ml/predict/behavior")
async def predict_behavior(user_id: str, message: str):
    """
    Klasyfikuje zachowanie użytkownika (positive/neutral/negative).

    Wymaga wcześniej wytrenowanego modelu dla tego użytkownika.

    Example:
        POST /api/v1/ml/predict/behavior
        Body: {"user_id": "user_123", "message": "Mam problem z pracą"}

    Response:
        {
            "status": "success",
            "user_id": "user_123",
            "prediction": {
                "predicted_class": "negative",
                "probabilities": {
                    "positive": 0.15,
                    "neutral": 0.25,
                    "negative": 0.60
                },
                "timestamp": "2025-12-03T12:00:00"
            }
        }
    """
    try:
        training = get_training_service()
        if not training:
            raise HTTPException(status_code=503, detail="ML Training Service not available")

        prediction = await training.predict_behavior(user_id=user_id, message=message)

        if prediction is None:
            raise HTTPException(
                status_code=404,
                detail=f"No trained behavior profiler model found for user {user_id}. Please train first."
            )

        return {
            "status": "success",
            "user_id": user_id,
            "prediction": prediction
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Behavior prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/ml/model/{user_id}/info")
async def get_model_info(user_id: str, model_type: str = "mood_predictor"):
    """
    Zwraca informacje o wytrenowanym modelu użytkownika.

    Args:
        user_id: ID użytkownika
        model_type: Typ modelu (mood_predictor lub behavior_profiler)

    Example:
        GET /api/v1/ml/model/user_123/info?model_type=mood_predictor

    Response:
        {
            "status": "success",
            "model_info": {
                "model_type": "mood_predictor",
                "trained_at": "2025-12-03T12:00:00",
                "n_samples": 150,
                "metrics": {...}
            }
        }
    """
    try:
        training = get_training_service()
        if not training:
            raise HTTPException(status_code=503, detail="ML Training Service not available")

        info = training.get_model_info(user_id, model_type)

        if info is None:
            raise HTTPException(
                status_code=404,
                detail=f"No {model_type} model found for user {user_id}"
            )

        return {
            "status": "success",
            "model_info": info
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get model info failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/ml/health")
async def ml_health():
    """Check ML Services status"""
    try:
        training = get_training_service()
        feature_eng = feature_engineer

        return {
            "status": "healthy" if (training and feature_eng) else "unavailable",
            "services": {
                "feature_engineer": "available" if feature_eng else "unavailable",
                "training_service": "available" if training else "unavailable"
            },
            "capabilities": {
                "mood_prediction": training is not None,
                "behavior_profiling": training is not None,
                "feature_extraction": feature_eng is not None
            }
        }

    except Exception as e:
        logger.error(f"ML health check failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================================
# NOTIFICATIONS - Real-time Smart Notifications
# ============================================================================

@app.get("/api/v1/notifications/{user_id}")
async def get_user_notifications(user_id: str, unread_only: bool = False, limit: int = 50):
    """
    Pobiera powiadomienia użytkownika.

    Example:
        GET /api/v1/notifications/user_123?unread_only=true&limit=20

    Response:
        {
            "status": "success",
            "user_id": "user_123",
            "total": 15,
            "notifications": [
                {
                    "notification_id": "mood_drop_user_123_...",
                    "type": "mood_drop",
                    "priority": "high",
                    "title": "Zauważyłem spadek nastroju",
                    "message": "...",
                    "created_at": "2025-12-03T12:00:00",
                    "read": false
                },
                ...
            ]
        }
    """
    try:
        notif_service = get_notification_service()
        if not notif_service:
            raise HTTPException(status_code=503, detail="Notification service not available")

        notifications = await notif_service.get_user_notifications(
            user_id=user_id,
            unread_only=unread_only,
            limit=limit
        )

        return {
            "status": "success",
            "user_id": user_id,
            "total": len(notifications),
            "notifications": notifications
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get notifications failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """
    Oznacza powiadomienie jako przeczytane.

    Example:
        POST /api/v1/notifications/mood_drop_user_123_.../read

    Response:
        {
            "status": "success",
            "notification_id": "mood_drop_user_123_...",
            "read": true
        }
    """
    try:
        notif_service = get_notification_service()
        if not notif_service:
            raise HTTPException(status_code=503, detail="Notification service not available")

        success = await notif_service.mark_as_read(notification_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Notification {notification_id} not found")

        return {
            "status": "success",
            "notification_id": notification_id,
            "read": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mark notification read failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/notifications/generate/daily-summary/{user_id}")
async def generate_daily_summary(user_id: str):
    """
    Generuje codzienne podsumowanie dla użytkownika.

    Example:
        POST /api/v1/notifications/generate/daily-summary/user_123

    Response:
        {
            "status": "success",
            "notification": {
                "type": "daily_summary",
                "title": "Twoje podsumowanie dnia",
                "message": "..."
            }
        }
    """
    try:
        notif_service = get_notification_service()
        if not notif_service:
            raise HTTPException(status_code=503, detail="Notification service not available")

        notification = await notif_service.generate_daily_summary(user_id)

        if not notification:
            raise HTTPException(status_code=500, detail="Failed to generate daily summary")

        return {
            "status": "success",
            "notification": notification.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate daily summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/notifications/generate/weekly-summary/{user_id}")
async def generate_weekly_summary(user_id: str):
    """
    Generuje tygodniowe podsumowanie dla użytkownika.

    Example:
        POST /api/v1/notifications/generate/weekly-summary/user_123

    Response:
        {
            "status": "success",
            "notification": {
                "type": "weekly_summary",
                "title": "Twoje podsumowanie tygodnia",
                "message": "..."
            }
        }
    """
    try:
        notif_service = get_notification_service()
        if not notif_service:
            raise HTTPException(status_code=503, detail="Notification service not available")

        notification = await notif_service.generate_weekly_summary(user_id)

        if not notification:
            raise HTTPException(status_code=500, detail="Failed to generate weekly summary")

        return {
            "status": "success",
            "notification": notification.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate weekly summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/notifications/health")
async def notifications_health():
    """Check Notification Service status"""
    try:
        notif_service = get_notification_service()

        if not notif_service:
            return {
                "status": "unavailable",
                "message": "Notification service not initialized"
            }

        return {
            "status": "healthy",
            "services": {
                "memory_manager": "available" if notif_service.memory else "unavailable",
                "ml_service": "available" if notif_service.ml_service else "unavailable",
                "analytics_service": "available" if notif_service.analytics else "unavailable"
            },
            "capabilities": {
                "mood_detection": True,
                "pattern_detection": True,
                "ml_predictions": notif_service.ml_service is not None,
                "summaries": True,
                "real_time_push": True
            }
        }

    except Exception as e:
        logger.error(f"Notification health check failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

