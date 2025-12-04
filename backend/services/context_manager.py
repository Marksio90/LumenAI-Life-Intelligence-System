"""
Advanced Context Management System

Features:
- Sliding window with automatic summarization
- Conversation threading
- Context compression
- Relevance scoring
- Memory pruning
- Token management
- Multi-turn dialogue handling
"""

import asyncio
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import tiktoken

from backend.core.logging_config import get_logger
from backend.services.rag import get_rag_pipeline, Document

logger = get_logger(__name__)


class MessageRole(str, Enum):
    """Message roles"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


@dataclass
class Message:
    """Conversation message"""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    relevance_score: float = 1.0


@dataclass
class ConversationThread:
    """Conversation thread with context"""
    thread_id: str
    user_id: str
    messages: List[Message] = field(default_factory=list)
    summary: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextWindow:
    """Sliding context window"""
    messages: List[Message]
    total_tokens: int
    summary: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextManager:
    """
    Advanced context management for conversations

    Features:
    - Sliding window (configurable size)
    - Automatic summarization when window is full
    - Conversation threading
    - Context compression
    - Relevance-based message pruning
    - Token counting and management
    - RAG integration for context retrieval
    """

    def __init__(
        self,
        max_context_tokens: int = 4000,
        max_history_length: int = 20,
        summarization_threshold: float = 0.8,
        model: str = "gpt-4"
    ):
        """
        Initialize Context Manager

        Args:
            max_context_tokens: Maximum tokens in context window
            max_history_length: Maximum messages to keep
            summarization_threshold: Trigger summarization at this % of max
            model: Model for token counting
        """
        self.max_context_tokens = max_context_tokens
        self.max_history_length = max_history_length
        self.summarization_threshold = summarization_threshold
        self.model = model

        # Token encoder
        self.encoder = tiktoken.encoding_for_model(model)

        # Storage
        self.threads: Dict[str, ConversationThread] = {}

        # RAG integration
        self.rag_pipeline = None  # Lazy init

        logger.info(f"Context manager initialized: max_tokens={max_context_tokens}, max_history={max_history_length}")

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        try:
            return len(self.encoder.encode(text))
        except Exception:
            return len(text) // 4

    def _get_rag_pipeline(self):
        """Lazy init RAG pipeline"""
        if self.rag_pipeline is None:
            self.rag_pipeline = get_rag_pipeline()
        return self.rag_pipeline

    async def create_thread(
        self,
        thread_id: str,
        user_id: str,
        initial_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationThread:
        """
        Create new conversation thread

        Args:
            thread_id: Unique thread identifier
            user_id: User identifier
            initial_message: Optional first message
            metadata: Optional thread metadata

        Returns:
            Created thread
        """
        thread = ConversationThread(
            thread_id=thread_id,
            user_id=user_id,
            metadata=metadata or {}
        )

        if initial_message:
            message = Message(
                role=MessageRole.SYSTEM,
                content=initial_message,
                token_count=self._count_tokens(initial_message)
            )
            thread.messages.append(message)

        self.threads[thread_id] = thread
        logger.info(f"Created thread: {thread_id} for user {user_id}")

        return thread

    async def add_message(
        self,
        thread_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Add message to thread

        Args:
            thread_id: Thread identifier
            role: Message role
            content: Message content
            metadata: Optional message metadata

        Returns:
            Created message
        """
        thread = self.threads.get(thread_id)
        if not thread:
            raise ValueError(f"Thread not found: {thread_id}")

        message = Message(
            role=role,
            content=content,
            metadata=metadata or {},
            token_count=self._count_tokens(content)
        )

        thread.messages.append(message)
        thread.updated_at = datetime.utcnow()

        logger.debug(f"Added message to thread {thread_id}: {role.value} ({message.token_count} tokens)")

        # Check if we need to compress context
        total_tokens = sum(m.token_count for m in thread.messages)
        if total_tokens > self.max_context_tokens * self.summarization_threshold:
            await self._compress_context(thread)

        return message

    async def get_context_window(
        self,
        thread_id: str,
        max_tokens: Optional[int] = None,
        include_summary: bool = True,
        use_rag: bool = False,
        rag_query: Optional[str] = None,
        rag_top_k: int = 3
    ) -> ContextWindow:
        """
        Get context window for thread

        Args:
            thread_id: Thread identifier
            max_tokens: Override max tokens
            include_summary: Include thread summary
            use_rag: Use RAG for context retrieval
            rag_query: Query for RAG (uses last message if not provided)
            rag_top_k: Number of RAG results

        Returns:
            Context window
        """
        thread = self.threads.get(thread_id)
        if not thread:
            raise ValueError(f"Thread not found: {thread_id}")

        max_tokens = max_tokens or self.max_context_tokens
        selected_messages = []
        total_tokens = 0

        # Add summary if available
        summary = None
        if include_summary and thread.summary:
            summary = thread.summary
            summary_tokens = self._count_tokens(summary)
            total_tokens += summary_tokens

        # Add messages from most recent backwards
        for message in reversed(thread.messages):
            if total_tokens + message.token_count <= max_tokens:
                selected_messages.insert(0, message)
                total_tokens += message.token_count
            else:
                break

        # Optionally retrieve relevant context from RAG
        rag_context = None
        if use_rag and thread.messages:
            query = rag_query or thread.messages[-1].content
            try:
                rag_pipeline = self._get_rag_pipeline()
                rag_result = await rag_pipeline.retrieve(
                    query=query,
                    top_k=rag_top_k,
                    filters={"user_id": thread.user_id}
                )

                if rag_result.documents:
                    rag_texts = [doc.text for doc in rag_result.documents]
                    rag_context = "\n\n".join(rag_texts)
                    rag_tokens = self._count_tokens(rag_context)

                    # Include RAG context if we have room
                    if total_tokens + rag_tokens <= max_tokens:
                        total_tokens += rag_tokens

            except Exception as e:
                logger.error(f"RAG context retrieval failed: {e}")

        window = ContextWindow(
            messages=selected_messages,
            total_tokens=total_tokens,
            summary=summary,
            metadata={
                "thread_id": thread_id,
                "message_count": len(selected_messages),
                "total_messages": len(thread.messages),
                "rag_context": rag_context,
                "window_utilization": f"{(total_tokens / max_tokens * 100):.1f}%"
            }
        )

        logger.debug(f"Context window for {thread_id}: {len(selected_messages)} messages, {total_tokens} tokens")
        return window

    async def _compress_context(self, thread: ConversationThread):
        """
        Compress context using summarization

        This should ideally call an LLM to summarize old messages,
        but for now we'll just keep a running summary.
        """
        # Keep most recent messages
        keep_count = self.max_history_length // 2
        recent_messages = thread.messages[-keep_count:]
        old_messages = thread.messages[:-keep_count]

        if old_messages:
            # Create simple summary (in production, use LLM)
            summary_parts = []

            if thread.summary:
                summary_parts.append(thread.summary)

            # Summarize old messages
            for msg in old_messages:
                summary_parts.append(f"{msg.role.value}: {msg.content[:100]}...")

            thread.summary = "\n".join(summary_parts)
            thread.messages = recent_messages

            logger.info(f"Compressed thread {thread.thread_id}: {len(old_messages)} messages summarized")

    async def prune_old_messages(
        self,
        thread_id: str,
        keep_count: int = 10,
        relevance_threshold: float = 0.5
    ):
        """
        Prune low-relevance messages

        Args:
            thread_id: Thread identifier
            keep_count: Minimum messages to keep
            relevance_threshold: Keep messages above this score
        """
        thread = self.threads.get(thread_id)
        if not thread:
            return

        if len(thread.messages) <= keep_count:
            return

        # Keep recent messages and high-relevance messages
        recent_messages = thread.messages[-keep_count:]
        old_messages = thread.messages[:-keep_count]

        relevant_old = [
            msg for msg in old_messages
            if msg.relevance_score >= relevance_threshold
        ]

        thread.messages = relevant_old + recent_messages
        logger.info(f"Pruned thread {thread_id}: kept {len(thread.messages)} messages")

    def calculate_relevance_scores(
        self,
        thread_id: str,
        query: str
    ):
        """
        Calculate relevance scores for messages based on query

        This is a placeholder - in production, use embeddings similarity
        """
        thread = self.threads.get(thread_id)
        if not thread:
            return

        query_lower = query.lower()

        for message in thread.messages:
            # Simple keyword matching (replace with embedding similarity)
            content_lower = message.content.lower()
            common_words = set(query_lower.split()) & set(content_lower.split())
            score = len(common_words) / max(len(query_lower.split()), 1)
            message.relevance_score = min(score * 2, 1.0)  # Scale to [0, 1]

    async def get_thread_summary(self, thread_id: str) -> Optional[str]:
        """Get thread summary"""
        thread = self.threads.get(thread_id)
        return thread.summary if thread else None

    async def get_thread_stats(self, thread_id: str) -> Dict[str, Any]:
        """Get thread statistics"""
        thread = self.threads.get(thread_id)
        if not thread:
            return {}

        total_tokens = sum(m.token_count for m in thread.messages)
        avg_message_length = total_tokens / len(thread.messages) if thread.messages else 0

        return {
            "thread_id": thread_id,
            "user_id": thread.user_id,
            "message_count": len(thread.messages),
            "total_tokens": total_tokens,
            "avg_message_length": avg_message_length,
            "has_summary": thread.summary is not None,
            "created_at": thread.created_at.isoformat(),
            "updated_at": thread.updated_at.isoformat()
        }

    async def delete_thread(self, thread_id: str) -> bool:
        """Delete conversation thread"""
        if thread_id in self.threads:
            del self.threads[thread_id]
            logger.info(f"Deleted thread: {thread_id}")
            return True
        return False

    def get_all_threads(self, user_id: Optional[str] = None) -> List[ConversationThread]:
        """Get all threads, optionally filtered by user"""
        if user_id:
            return [t for t in self.threads.values() if t.user_id == user_id]
        return list(self.threads.values())


# Global instance
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """Get or create global context manager"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager
