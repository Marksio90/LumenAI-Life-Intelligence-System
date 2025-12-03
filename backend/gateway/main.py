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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global orchestrator, memory_manager

    logger.info("🚀 Starting LumenAI...")

    # Initialize core systems
    memory_manager = MemoryManager()
    orchestrator = Orchestrator(memory_manager)

    logger.info("✅ LumenAI initialized successfully")

    yield

    # Cleanup
    logger.info("🛑 Shutting down LumenAI...")


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
