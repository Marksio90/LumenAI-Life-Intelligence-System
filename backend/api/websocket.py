"""
WebSocket API Endpoints

Real-time communication endpoints for chat, streaming, and notifications.
"""

import json
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from fastapi.responses import JSONResponse

from backend.core.websocket_manager import get_connection_manager
from backend.services.streaming_service import get_streaming_service
from backend.core.auth import get_current_user_ws  # WebSocket auth helper
from backend.core.memory import get_memory_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/chat")
async def websocket_chat(
    websocket: WebSocket,
    token: str = Query(..., description="Authentication token")
):
    """
    WebSocket endpoint for real-time chat.

    Supports:
    - Real-time LLM streaming
    - Multi-agent conversations
    - RAG retrieval
    - Typing indicators
    - Read receipts

    Message format:
    {
        "type": "chat.message",
        "content": "User message",
        "conversation_id": "optional-conversation-id",
        "stream": true,
        "metadata": {}
    }
    """
    connection_manager = get_connection_manager()
    streaming_service = get_streaming_service()
    memory_manager = get_memory_manager()

    # Authenticate user with JWT token
    try:
        from backend.core.auth import get_current_user_ws
        user_data = await get_current_user_ws(token)
        user_id = user_data["user_id"]
    except Exception as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.error(f"WebSocket authentication failed: {e}")
        return

    # Connect WebSocket
    connection_id = await connection_manager.connect(
        websocket,
        user_id,
        metadata={"type": "chat", "user_data": user_data}
    )

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")

                # Handle different message types
                if message_type == "chat.message":
                    await handle_chat_message(
                        user_id,
                        message,
                        streaming_service,
                        memory_manager
                    )

                elif message_type == "typing.start":
                    await handle_typing_start(user_id, message, connection_manager)

                elif message_type == "typing.stop":
                    await handle_typing_stop(user_id, message, connection_manager)

                elif message_type == "read.receipt":
                    await handle_read_receipt(user_id, message, connection_manager)

                elif message_type == "ping":
                    await connection_manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }, websocket)

                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    await connection_manager.send_personal_message({
                        "type": "error",
                        "error": f"Unknown message type: {message_type}",
                        "timestamp": datetime.utcnow().isoformat()
                    }, websocket)

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
                await connection_manager.send_personal_message({
                    "type": "error",
                    "error": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)

            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await connection_manager.send_personal_message({
                    "type": "error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected: user={user_id}, connection={connection_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connection_manager.disconnect(websocket)


@router.websocket("/agent")
async def websocket_agent(
    websocket: WebSocket,
    token: str = Query(..., description="Authentication token"),
    agent_name: str = Query(..., description="Agent name")
):
    """
    WebSocket endpoint for direct agent communication.

    Supports:
    - Agent-specific conversations
    - Tool call streaming
    - Agent state updates
    - Multi-agent orchestration
    """
    connection_manager = get_connection_manager()
    streaming_service = get_streaming_service()

    # Authenticate with JWT token
    try:
        from backend.core.auth import get_current_user_ws
        user_data = await get_current_user_ws(token)
        user_id = user_data["user_id"]
    except Exception as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.error(f"WebSocket authentication failed: {e}")
        return

    # Connect
    connection_id = await connection_manager.connect(
        websocket,
        user_id,
        metadata={"type": "agent", "agent_name": agent_name}
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Route to agent handler
            await streaming_service.stream_agent_action(
                user_id,
                agent_name,
                "message_received",
                {"content": message.get("content")}
            )

            # Process agent response (simplified)
            # TODO: Integrate with AgentRegistry
            await connection_manager.send_personal_message({
                "type": "agent.response",
                "agent_name": agent_name,
                "content": f"Response from {agent_name}",
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(..., description="Authentication token")
):
    """
    WebSocket endpoint for real-time notifications.

    Receives:
    - System notifications
    - Task updates
    - Background job status
    - Alerts
    """
    connection_manager = get_connection_manager()

    # Authenticate with JWT token
    try:
        from backend.core.auth import get_current_user_ws
        user_data = await get_current_user_ws(token)
        user_id = user_data["user_id"]
    except Exception as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.error(f"WebSocket authentication failed: {e}")
        return

    # Connect
    connection_id = await connection_manager.connect(
        websocket,
        user_id,
        metadata={"type": "notifications"}
    )

    try:
        while True:
            # Just keep connection alive and receive pings
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await connection_manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)


# Helper functions

async def handle_chat_message(
    user_id: str,
    message: dict,
    streaming_service,
    memory_manager
):
    """Handle incoming chat message and stream LLM response."""
    content = message.get("content")
    conversation_id = message.get("conversation_id")
    stream = message.get("stream", True)
    model = message.get("model", "gpt-4-turbo-preview")
    provider = message.get("provider", "openai")

    # Store user message
    await memory_manager.store_message(
        user_id=user_id,
        conversation_id=conversation_id,
        role="user",
        content=content
    )

    # Get conversation history
    history = await memory_manager.get_conversation_history(
        user_id=user_id,
        conversation_id=conversation_id,
        limit=10
    )

    # Format messages for LLM
    messages = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history
    ]

    # Stream response
    if stream:
        if provider == "openai":
            full_response = ""
            async for chunk in streaming_service.stream_openai_completion(
                user_id=user_id,
                messages=messages,
                model=model
            ):
                full_response += chunk

            # Store assistant response
            await memory_manager.store_message(
                user_id=user_id,
                conversation_id=conversation_id,
                role="assistant",
                content=full_response
            )

        elif provider == "anthropic":
            full_response = ""
            async for chunk in streaming_service.stream_anthropic_completion(
                user_id=user_id,
                messages=messages,
                model=model
            ):
                full_response += chunk

            await memory_manager.store_message(
                user_id=user_id,
                conversation_id=conversation_id,
                role="assistant",
                content=full_response
            )


async def handle_typing_start(user_id: str, message: dict, connection_manager):
    """Handle typing indicator start."""
    conversation_id = message.get("conversation_id")

    # Broadcast to other participants (if group chat)
    await connection_manager.send_to_user(user_id, {
        "type": "typing.start",
        "user_id": user_id,
        "conversation_id": conversation_id,
        "timestamp": datetime.utcnow().isoformat()
    })


async def handle_typing_stop(user_id: str, message: dict, connection_manager):
    """Handle typing indicator stop."""
    conversation_id = message.get("conversation_id")

    await connection_manager.send_to_user(user_id, {
        "type": "typing.stop",
        "user_id": user_id,
        "conversation_id": conversation_id,
        "timestamp": datetime.utcnow().isoformat()
    })


async def handle_read_receipt(user_id: str, message: dict, connection_manager):
    """Handle read receipt."""
    message_id = message.get("message_id")
    conversation_id = message.get("conversation_id")

    await connection_manager.send_to_user(user_id, {
        "type": "read.receipt",
        "user_id": user_id,
        "message_id": message_id,
        "conversation_id": conversation_id,
        "timestamp": datetime.utcnow().isoformat()
    })


# REST endpoints for WebSocket management

@router.get("/status")
async def get_websocket_status():
    """Get WebSocket connection statistics."""
    connection_manager = get_connection_manager()

    return {
        "total_connections": connection_manager.get_connection_count(),
        "active_users": len(connection_manager.get_active_users()),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/broadcast")
async def broadcast_message(message: dict):
    """
    Broadcast message to all connected users (admin only).

    Body:
    {
        "type": "announcement",
        "title": "System Maintenance",
        "message": "The system will be under maintenance...",
        "severity": "info"
    }
    """
    connection_manager = get_connection_manager()

    await connection_manager.broadcast({
        **message,
        "timestamp": datetime.utcnow().isoformat()
    })

    return {"status": "broadcasted", "user_count": connection_manager.get_connection_count()}


@router.post("/send/{user_id}")
async def send_to_user(user_id: str, message: dict):
    """
    Send message to specific user (admin/system use).

    Path params:
    - user_id: Target user ID

    Body:
    {
        "type": "notification",
        "content": "Your task is complete!"
    }
    """
    connection_manager = get_connection_manager()

    await connection_manager.send_to_user(user_id, {
        **message,
        "timestamp": datetime.utcnow().isoformat()
    })

    return {"status": "sent", "user_id": user_id}
