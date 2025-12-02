"""
LumenAI Memory Management System
Handles user context, conversation history, and long-term memory
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
import json
from collections import defaultdict


class MemoryManager:
    """
    Manages user memory and context
    - Short-term: Recent conversation
    - Long-term: User profile, preferences, habits
    - Episodic: Important events and milestones
    """

    def __init__(self):
        # In-memory storage (will be replaced with vector DB)
        self.user_conversations: Dict[str, List[Dict]] = defaultdict(list)
        self.user_profiles: Dict[str, Dict] = {}
        self.user_context_cache: Dict[str, Dict] = {}

        logger.info("💾 Memory Manager initialized")

    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive user context for processing
        """
        # Check cache first
        if user_id in self.user_context_cache:
            cache_time = self.user_context_cache[user_id].get("_cached_at")
            if cache_time and (datetime.utcnow() - cache_time).seconds < 300:  # 5 min cache
                return self.user_context_cache[user_id]

        # Build fresh context
        context = {
            "user_id": user_id,
            "recent_messages": await self._get_recent_messages(user_id, limit=10),
            "user_profile": self.user_profiles.get(user_id, {}),
            "recent_summary": await self._generate_recent_summary(user_id),
            "preferences": await self._get_user_preferences(user_id),
            "_cached_at": datetime.utcnow()
        }

        # Cache it
        self.user_context_cache[user_id] = context

        return context

    async def _get_recent_messages(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation messages"""
        if user_id not in self.user_conversations:
            return []

        messages = self.user_conversations[user_id][-limit:]
        return messages

    async def _generate_recent_summary(self, user_id: str) -> str:
        """Generate summary of recent interactions"""
        recent = await self._get_recent_messages(user_id, limit=5)

        if not recent:
            return "No recent conversation history"

        # Simple summary (will be enhanced with LLM)
        topics = []
        for msg in recent:
            if msg.get("agent"):
                topics.append(msg["agent"])

        if topics:
            return f"Recent topics: {', '.join(set(topics))}"
        return "General conversation"

    async def _get_user_preferences(self, user_id: str) -> Dict:
        """Get user preferences and settings"""
        profile = self.user_profiles.get(user_id, {})
        return profile.get("preferences", {
            "language": "pl",
            "tone": "friendly",
            "response_length": "medium"
        })

    async def store_interaction(
        self,
        user_id: str,
        message: str,
        response: str,
        agent: str,
        metadata: Optional[Dict] = None
    ):
        """
        Store interaction in memory
        """
        interaction = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_message": message,
            "assistant_response": response,
            "agent": agent,
            "metadata": metadata or {}
        }

        self.user_conversations[user_id].append(interaction)

        # Keep only last 1000 messages per user (memory management)
        if len(self.user_conversations[user_id]) > 1000:
            self.user_conversations[user_id] = self.user_conversations[user_id][-1000:]

        # Invalidate cache
        if user_id in self.user_context_cache:
            del self.user_context_cache[user_id]

        logger.debug(f"Stored interaction for {user_id}")

    async def get_user_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get user's conversation history"""
        if user_id not in self.user_conversations:
            return []

        return self.user_conversations[user_id][-limit:]

    async def clear_user_memory(self, user_id: str):
        """Clear all memory for user (privacy)"""
        if user_id in self.user_conversations:
            del self.user_conversations[user_id]
        if user_id in self.user_profiles:
            del self.user_profiles[user_id]
        if user_id in self.user_context_cache:
            del self.user_context_cache[user_id]

        logger.info(f"Cleared all memory for user {user_id}")

    async def update_user_profile(self, user_id: str, profile_data: Dict):
        """Update user profile information"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                "created_at": datetime.utcnow().isoformat(),
                "preferences": {}
            }

        self.user_profiles[user_id].update(profile_data)
        self.user_profiles[user_id]["updated_at"] = datetime.utcnow().isoformat()

        logger.info(f"Updated profile for {user_id}")

    async def search_memories(self, user_id: str, query: str, limit: int = 5) -> List[Dict]:
        """
        Search through user's memories (semantic search)
        TODO: Implement with vector database
        """
        if user_id not in self.user_conversations:
            return []

        # Simple keyword search for now
        results = []
        query_lower = query.lower()

        for interaction in reversed(self.user_conversations[user_id]):
            if (query_lower in interaction["user_message"].lower() or
                query_lower in interaction["assistant_response"].lower()):
                results.append(interaction)

            if len(results) >= limit:
                break

        return results
