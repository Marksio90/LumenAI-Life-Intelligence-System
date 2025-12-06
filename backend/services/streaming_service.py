"""
Streaming Service for Real-time LLM Responses

Handles streaming of LLM responses, tool calls, and agent actions
to connected WebSocket clients.
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional, Dict, Any, List
from datetime import datetime
from uuid import uuid4

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from core.websocket_manager import get_connection_manager

logger = logging.getLogger(__name__)


class StreamingService:
    """
    Service for streaming LLM responses and agent actions.

    Features:
    - Real-time token streaming
    - Tool call streaming
    - Multi-model support (OpenAI, Anthropic)
    - Context management
    - Error handling with recovery
    """

    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self.connection_manager = get_connection_manager()
        logger.info("StreamingService initialized")

    def _get_openai_client(self) -> AsyncOpenAI:
        """Lazy initialization of OpenAI client."""
        if not self.openai_client:
            import os
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            self.openai_client = AsyncOpenAI(api_key=api_key)
        return self.openai_client

    def _get_anthropic_client(self) -> AsyncAnthropic:
        """Lazy initialization of Anthropic client."""
        if not self.anthropic_client:
            import os
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            self.anthropic_client = AsyncAnthropic(api_key=api_key)
        return self.anthropic_client

    async def stream_openai_completion(
        self,
        user_id: str,
        messages: List[Dict[str, str]],
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream_id: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream OpenAI completion to user via WebSocket.

        Args:
            user_id: Target user ID
            messages: Conversation messages
            model: OpenAI model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream_id: Optional stream identifier
            **kwargs: Additional OpenAI parameters

        Yields:
            Text chunks from the completion
        """
        stream_id = stream_id or str(uuid4())
        client = self._get_openai_client()

        try:
            # Notify stream start
            await self.connection_manager.send_to_user(user_id, {
                "type": "llm.stream.start",
                "stream_id": stream_id,
                "model": model,
                "provider": "openai",
                "timestamp": datetime.utcnow().isoformat()
            })

            # Create streaming completion
            stream = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )

            full_response = ""
            chunk_count = 0

            # Stream chunks
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    chunk_count += 1

                    # Send chunk to user
                    await self.connection_manager.send_to_user(user_id, {
                        "type": "llm.stream.chunk",
                        "stream_id": stream_id,
                        "content": content,
                        "chunk_index": chunk_count,
                        "timestamp": datetime.utcnow().isoformat()
                    })

                    yield content

                    # Small delay to prevent overwhelming
                    await asyncio.sleep(0.01)

                # Handle function calls
                if chunk.choices and chunk.choices[0].delta.function_call:
                    function_call = chunk.choices[0].delta.function_call
                    await self.connection_manager.send_to_user(user_id, {
                        "type": "llm.function_call",
                        "stream_id": stream_id,
                        "function_name": function_call.name,
                        "arguments": function_call.arguments,
                        "timestamp": datetime.utcnow().isoformat()
                    })

            # Notify stream end
            await self.connection_manager.send_to_user(user_id, {
                "type": "llm.stream.end",
                "stream_id": stream_id,
                "total_chunks": chunk_count,
                "full_response": full_response,
                "timestamp": datetime.utcnow().isoformat()
            })

            logger.info(
                f"OpenAI stream completed: user={user_id}, "
                f"chunks={chunk_count}, model={model}"
            )

        except Exception as e:
            logger.error(f"Error streaming OpenAI completion: {e}")

            # Notify error
            await self.connection_manager.send_to_user(user_id, {
                "type": "llm.stream.error",
                "stream_id": stream_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

            raise

    async def stream_anthropic_completion(
        self,
        user_id: str,
        messages: List[Dict[str, str]],
        model: str = "claude-3-opus-20240229",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream_id: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream Anthropic (Claude) completion to user via WebSocket.

        Args:
            user_id: Target user ID
            messages: Conversation messages
            model: Claude model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream_id: Optional stream identifier
            **kwargs: Additional Anthropic parameters

        Yields:
            Text chunks from the completion
        """
        stream_id = stream_id or str(uuid4())
        client = self._get_anthropic_client()

        try:
            # Notify stream start
            await self.connection_manager.send_to_user(user_id, {
                "type": "llm.stream.start",
                "stream_id": stream_id,
                "model": model,
                "provider": "anthropic",
                "timestamp": datetime.utcnow().isoformat()
            })

            # Create streaming completion
            async with client.messages.stream(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            ) as stream:
                full_response = ""
                chunk_count = 0

                async for text in stream.text_stream:
                    full_response += text
                    chunk_count += 1

                    # Send chunk to user
                    await self.connection_manager.send_to_user(user_id, {
                        "type": "llm.stream.chunk",
                        "stream_id": stream_id,
                        "content": text,
                        "chunk_index": chunk_count,
                        "timestamp": datetime.utcnow().isoformat()
                    })

                    yield text

                    await asyncio.sleep(0.01)

            # Notify stream end
            await self.connection_manager.send_to_user(user_id, {
                "type": "llm.stream.end",
                "stream_id": stream_id,
                "total_chunks": chunk_count,
                "full_response": full_response,
                "timestamp": datetime.utcnow().isoformat()
            })

            logger.info(
                f"Anthropic stream completed: user={user_id}, "
                f"chunks={chunk_count}, model={model}"
            )

        except Exception as e:
            logger.error(f"Error streaming Anthropic completion: {e}")

            await self.connection_manager.send_to_user(user_id, {
                "type": "llm.stream.error",
                "stream_id": stream_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

            raise

    async def stream_agent_action(
        self,
        user_id: str,
        agent_name: str,
        action_type: str,
        action_data: Dict[str, Any],
        stream_id: Optional[str] = None
    ):
        """
        Stream agent action to user.

        Args:
            user_id: Target user ID
            agent_name: Name of the agent performing the action
            action_type: Type of action (thinking, tool_call, response, etc.)
            action_data: Action-specific data
            stream_id: Optional stream identifier
        """
        stream_id = stream_id or str(uuid4())

        await self.connection_manager.send_to_user(user_id, {
            "type": "agent.action",
            "stream_id": stream_id,
            "agent_name": agent_name,
            "action_type": action_type,
            "action_data": action_data,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def stream_rag_retrieval(
        self,
        user_id: str,
        query: str,
        documents: List[Dict[str, Any]],
        stream_id: Optional[str] = None
    ):
        """
        Stream RAG retrieval results to user.

        Args:
            user_id: Target user ID
            query: Search query
            documents: Retrieved documents
            stream_id: Optional stream identifier
        """
        stream_id = stream_id or str(uuid4())

        await self.connection_manager.send_to_user(user_id, {
            "type": "rag.retrieval",
            "stream_id": stream_id,
            "query": query,
            "document_count": len(documents),
            "documents": documents,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def stream_progress(
        self,
        user_id: str,
        task_id: str,
        progress: float,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Stream progress update to user.

        Args:
            user_id: Target user ID
            task_id: Task identifier
            progress: Progress percentage (0-100)
            message: Progress message
            metadata: Optional additional metadata
        """
        await self.connection_manager.send_to_user(user_id, {
            "type": "task.progress",
            "task_id": task_id,
            "progress": progress,
            "message": message,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        })

    async def stream_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        severity: str = "info",
        action_url: Optional[str] = None
    ):
        """
        Stream notification to user.

        Args:
            user_id: Target user ID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            severity: Severity level (info, warning, error, success)
            action_url: Optional action URL
        """
        await self.connection_manager.send_to_user(user_id, {
            "type": "notification",
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "severity": severity,
            "action_url": action_url,
            "timestamp": datetime.utcnow().isoformat()
        })


# Global instance
_streaming_service = None


def get_streaming_service() -> StreamingService:
    """Get or create the global StreamingService instance."""
    global _streaming_service
    if _streaming_service is None:
        _streaming_service = StreamingService()
    return _streaming_service
