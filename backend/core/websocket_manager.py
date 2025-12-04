"""
WebSocket Manager for Real-time Communication

Handles WebSocket connections, message routing, and connection lifecycle.
Supports multiple concurrent connections per user.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time communication.

    Features:
    - User-based connection grouping
    - Broadcast to all connections
    - Broadcast to specific user
    - Connection health monitoring
    - Automatic reconnection handling
    """

    def __init__(self):
        # Active connections: user_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}

        # Connection metadata: connection_id -> metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

        # Reverse mapping: websocket -> connection_id
        self.websocket_to_id: Dict[WebSocket, str] = {}

        # Message queue for offline users (optional)
        self.message_queue: Dict[str, list] = {}

        logger.info("WebSocket ConnectionManager initialized")

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            user_id: User identifier
            metadata: Optional connection metadata

        Returns:
            connection_id: Unique connection identifier
        """
        await websocket.accept()

        # Generate unique connection ID
        connection_id = str(uuid4())

        # Register connection
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)
        self.websocket_to_id[websocket] = connection_id

        # Store metadata
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "connection_id": connection_id,
            "connected_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            **(metadata or {})
        }

        logger.info(
            f"WebSocket connected: user={user_id}, "
            f"connection={connection_id}, "
            f"total_connections={self.get_connection_count(user_id)}"
        )

        # Send welcome message
        await self.send_personal_message({
            "type": "connection.established",
            "connection_id": connection_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)

        # Send any queued messages
        if user_id in self.message_queue:
            for message in self.message_queue[user_id]:
                await self.send_personal_message(message, websocket)
            self.message_queue[user_id].clear()

        return connection_id

    def disconnect(self, websocket: WebSocket):
        """
        Disconnect and unregister a WebSocket connection.

        Args:
            websocket: The WebSocket connection to disconnect
        """
        connection_id = self.websocket_to_id.get(websocket)

        if not connection_id:
            logger.warning("Attempted to disconnect unknown WebSocket")
            return

        metadata = self.connection_metadata.get(connection_id, {})
        user_id = metadata.get("user_id")

        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

            # Clean up empty user entry
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        # Clean up metadata
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]

        if websocket in self.websocket_to_id:
            del self.websocket_to_id[websocket]

        logger.info(
            f"WebSocket disconnected: user={user_id}, "
            f"connection={connection_id}"
        )

    async def send_personal_message(
        self,
        message: Dict[str, Any],
        websocket: WebSocket
    ):
        """
        Send a message to a specific WebSocket connection.

        Args:
            message: Message dictionary to send
            websocket: Target WebSocket connection
        """
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)

                # Update last activity
                connection_id = self.websocket_to_id.get(websocket)
                if connection_id and connection_id in self.connection_metadata:
                    self.connection_metadata[connection_id]["last_activity"] = \
                        datetime.utcnow().isoformat()
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """
        Send a message to all connections of a specific user.

        Args:
            user_id: Target user ID
            message: Message dictionary to send
        """
        if user_id not in self.active_connections:
            # Queue message for offline user
            if user_id not in self.message_queue:
                self.message_queue[user_id] = []
            self.message_queue[user_id].append(message)
            logger.debug(f"Message queued for offline user: {user_id}")
            return

        # Send to all user's connections
        disconnected = []
        for websocket in self.active_connections[user_id]:
            try:
                await self.send_personal_message(message, websocket)
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
                disconnected.append(websocket)

        # Clean up disconnected sockets
        for websocket in disconnected:
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast a message to all connected users.

        Args:
            message: Message dictionary to broadcast
        """
        disconnected = []

        for user_id, connections in self.active_connections.items():
            for websocket in connections:
                try:
                    await self.send_personal_message(message, websocket)
                except Exception as e:
                    logger.error(f"Error broadcasting to {user_id}: {e}")
                    disconnected.append(websocket)

        # Clean up disconnected sockets
        for websocket in disconnected:
            self.disconnect(websocket)

    async def stream_to_user(
        self,
        user_id: str,
        stream_id: str,
        data_generator,
        chunk_type: str = "text"
    ):
        """
        Stream data to a user in real-time.

        Args:
            user_id: Target user ID
            stream_id: Unique stream identifier
            data_generator: Async generator yielding data chunks
            chunk_type: Type of data being streamed (text, audio, etc.)
        """
        # Send stream start event
        await self.send_to_user(user_id, {
            "type": "stream.start",
            "stream_id": stream_id,
            "chunk_type": chunk_type,
            "timestamp": datetime.utcnow().isoformat()
        })

        try:
            # Stream chunks
            async for chunk in data_generator:
                await self.send_to_user(user_id, {
                    "type": "stream.chunk",
                    "stream_id": stream_id,
                    "chunk_type": chunk_type,
                    "data": chunk,
                    "timestamp": datetime.utcnow().isoformat()
                })

                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.01)

            # Send stream end event
            await self.send_to_user(user_id, {
                "type": "stream.end",
                "stream_id": stream_id,
                "timestamp": datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"Error streaming to user {user_id}: {e}")

            # Send stream error event
            await self.send_to_user(user_id, {
                "type": "stream.error",
                "stream_id": stream_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

    def get_connection_count(self, user_id: Optional[str] = None) -> int:
        """
        Get the number of active connections.

        Args:
            user_id: If provided, count only this user's connections

        Returns:
            Number of active connections
        """
        if user_id:
            return len(self.active_connections.get(user_id, set()))

        return sum(len(conns) for conns in self.active_connections.values())

    def get_active_users(self) -> Set[str]:
        """
        Get set of all users with active connections.

        Returns:
            Set of user IDs
        """
        return set(self.active_connections.keys())

    def get_connection_metadata(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific connection.

        Args:
            connection_id: Connection identifier

        Returns:
            Connection metadata or None
        """
        return self.connection_metadata.get(connection_id)

    async def ping_all(self):
        """
        Send ping to all connections to check health.
        Useful for keep-alive and detecting dead connections.
        """
        await self.broadcast({
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat()
        })


# Global instance
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global ConnectionManager instance."""
    return manager
