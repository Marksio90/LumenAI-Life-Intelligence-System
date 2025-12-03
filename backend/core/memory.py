"""
LumenAI Memory Management System
Handles user context, conversation history, and long-term memory

UPDATED: Now uses MongoDB for persistent storage!
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
import json
from collections import defaultdict
import uuid


class MemoryManager:
    """
    Manages user memory and context
    - Short-term: Recent conversation
    - Long-term: User profile, preferences, habits
    - Episodic: Important events and milestones

    NOW WITH MONGODB PERSISTENCE! 🎉
    """

    def __init__(self):
        # In-memory cache (for performance)
        self.user_context_cache: Dict[str, Dict] = {}
        self.active_conversations: Dict[str, str] = {}  # user_id -> conversation_id

        # MongoDB will be used for persistent storage
        # Accessed via: get_mongodb_service()

        logger.info("💾 Memory Manager initialized (with MongoDB persistence)")

    def _get_db(self):
        """Helper to get MongoDB service (returns None if not connected)"""
        try:
            from backend.services.mongodb_service import get_mongodb_service
            return get_mongodb_service()
        except:
            return None

    async def _ensure_user_exists(self, user_id: str):
        """Ensure user exists in database"""
        db = self._get_db()
        if not db:
            return

        user = await db.get_user(user_id)
        if not user:
            from backend.models.database import User
            new_user = User(user_id=user_id)
            await db.create_user(new_user)
            logger.info(f"✅ Created new user: {user_id}")

    async def _get_or_create_conversation(self, user_id: str) -> str:
        """Get active conversation ID or create new one"""
        # Check if user has active conversation in cache
        if user_id in self.active_conversations:
            return self.active_conversations[user_id]

        db = self._get_db()
        if not db:
            # Fallback: generate conversation_id even without DB
            conv_id = f"conv_{uuid.uuid4().hex[:16]}"
            self.active_conversations[user_id] = conv_id
            return conv_id

        # Ensure user exists
        await self._ensure_user_exists(user_id)

        # Get recent conversations
        conversations = await db.get_user_conversations(user_id, limit=1, status="active")

        if conversations and len(conversations) > 0:
            # Use most recent active conversation
            conv_id = conversations[0].conversation_id
        else:
            # Create new conversation
            from backend.models.database import Conversation
            conv_id = f"conv_{uuid.uuid4().hex[:16]}"
            new_conv = Conversation(
                conversation_id=conv_id,
                user_id=user_id,
                title="Nowa rozmowa"
            )
            await db.create_conversation(new_conv)
            logger.info(f"✅ Created new conversation: {conv_id}")

        # Cache it
        self.active_conversations[user_id] = conv_id
        return conv_id

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
            "user_profile": await self._get_user_profile(user_id),
            "recent_summary": await self._generate_recent_summary(user_id),
            "preferences": await self._get_user_preferences(user_id),
            "_cached_at": datetime.utcnow()
        }

        # Cache it
        self.user_context_cache[user_id] = context

        return context

    async def _get_recent_messages(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation messages (from MongoDB)"""
        db = self._get_db()
        if not db:
            return []

        # Get recent messages from MongoDB
        messages = await db.get_recent_messages(user_id, limit=limit)

        # Convert to dict format expected by rest of code
        return [
            {
                "timestamp": msg.timestamp.isoformat(),
                "role": msg.role,
                "content": msg.content,
                "agent": msg.agent
            }
            for msg in messages
        ]

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

    async def _get_user_profile(self, user_id: str) -> Dict:
        """Get user profile information (from MongoDB)"""
        db = self._get_db()
        if not db:
            return {}

        user = await db.get_user(user_id)
        if user and user.profile:
            return {
                "name": user.profile.name,
                "age": user.profile.age,
                "timezone": user.profile.timezone,
                "interests": user.profile.interests,
                "goals": user.profile.goals
            }
        return {}

    async def _get_user_preferences(self, user_id: str) -> Dict:
        """Get user preferences and settings (from MongoDB)"""
        db = self._get_db()
        if not db:
            return {
                "language": "pl",
                "tone": "friendly",
                "response_length": "medium"
            }

        user = await db.get_user(user_id)
        if user and user.preferences:
            return {
                "language": user.profile.language if user.profile else "pl",
                "model": user.preferences.model,
                "temperature": user.preferences.temperature
            }

        return {
            "language": "pl",
            "tone": "friendly",
            "response_length": "medium"
        }

    async def store_interaction(
        self,
        user_id: str,
        message: str,
        response: str,
        agent: str,
        metadata: Optional[Dict] = None
    ):
        """
        Store interaction in MongoDB (persistent storage!)

        Zapisuje DWA messages:
        1. Wiadomość użytkownika (role="user")
        2. Odpowiedź asystenta (role="assistant")
        """
        db = self._get_db()
        if not db:
            logger.warning("MongoDB not available, interaction not persisted")
            return

        # Get or create conversation
        conversation_id = await self._get_or_create_conversation(user_id)

        from backend.models.database import Message, MessageMetadata

        # 1. Zapisz wiadomość użytkownika
        user_msg_id = f"msg_{uuid.uuid4().hex[:16]}"
        user_message = Message(
            message_id=user_msg_id,
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=message,
            agent=None
        )
        await db.create_message(user_message)

        # 2. Zapisz odpowiedź asystenta
        assistant_msg_id = f"msg_{uuid.uuid4().hex[:16]}"
        assistant_message = Message(
            message_id=assistant_msg_id,
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=response,
            agent=agent,
            metadata=MessageMetadata(**(metadata or {}))
        )
        await db.create_message(assistant_message)

        # Invalidate cache
        if user_id in self.user_context_cache:
            del self.user_context_cache[user_id]

        logger.debug(f"💾 Stored interaction for {user_id} in conversation {conversation_id}")

    async def get_user_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get user's conversation history (from MongoDB)"""
        db = self._get_db()
        if not db:
            return []

        # Get recent messages
        messages = await db.get_recent_messages(user_id, limit=limit)

        # Convert to dict format
        return [
            {
                "timestamp": msg.timestamp.isoformat(),
                "role": msg.role,
                "content": msg.content,
                "agent": msg.agent,
                "conversation_id": msg.conversation_id
            }
            for msg in reversed(messages)  # Reverse to get chronological order
        ]

    async def clear_user_memory(self, user_id: str):
        """Clear all memory for user (privacy) - ONLY FROM CACHE, not MongoDB!"""
        # Clear cache
        if user_id in self.user_context_cache:
            del self.user_context_cache[user_id]
        if user_id in self.active_conversations:
            del self.active_conversations[user_id]

        # NOTE: We don't delete from MongoDB for data safety
        # If you want to delete from DB, use MongoDB service directly
        logger.info(f"Cleared cache for user {user_id} (MongoDB data preserved)")

    async def update_user_profile(self, user_id: str, profile_data: Dict):
        """Update user profile information (in MongoDB)"""
        db = self._get_db()
        if not db:
            logger.warning("MongoDB not available, profile not updated")
            return

        # Ensure user exists
        await self._ensure_user_exists(user_id)

        # Update user
        await db.update_user(user_id, profile_data)

        # Invalidate cache
        if user_id in self.user_context_cache:
            del self.user_context_cache[user_id]

        logger.info(f"Updated profile for {user_id}")

    async def search_memories(self, user_id: str, query: str, limit: int = 5) -> List[Dict]:
        """
        Search through user's memories (simple keyword search for now)
        TODO: Implement with vector database (ChromaDB) for semantic search
        """
        db = self._get_db()
        if not db:
            return []

        # Get all recent messages (we'll search through them)
        messages = await db.get_recent_messages(user_id, limit=100)

        # Simple keyword search
        results = []
        query_lower = query.lower()

        for msg in messages:
            if query_lower in msg.content.lower():
                results.append({
                    "timestamp": msg.timestamp.isoformat(),
                    "role": msg.role,
                    "content": msg.content,
                    "agent": msg.agent,
                    "conversation_id": msg.conversation_id
                })

            if len(results) >= limit:
                break

        return results

    async def save_mood_entry(
        self,
        user_id: str,
        mood_data: Dict[str, Any],
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Save mood entry to MongoDB

        Args:
            user_id: User ID
            mood_data: Dict with mood information:
                - primary: Main mood (e.g., "happy", "sad", "anxious")
                - intensity: 1-10
                - secondary: List of additional emotions (optional)
                - description: User's description (optional)
                - triggers: List of triggers (optional)
                - situation: Context (optional)
            conversation_id: ID rozmowy (optional)
            message_id: ID wiadomości (optional)

        Returns:
            entry_id if saved, None if MongoDB not available
        """
        db = self._get_db()
        if not db:
            logger.warning("MongoDB not available, mood entry not saved")
            return None

        from backend.models.database import MoodEntry, MoodData, MoodContext, MoodIntervention

        # Generate entry_id
        entry_id = f"mood_{uuid.uuid4().hex[:16]}"

        # Create mood entry
        mood_entry = MoodEntry(
            entry_id=entry_id,
            user_id=user_id,
            mood=MoodData(
                primary=mood_data.get("primary", "neutral"),
                intensity=mood_data.get("intensity", 5),
                secondary=mood_data.get("secondary", []),
                description=mood_data.get("description")
            ),
            context=MoodContext(
                triggers=mood_data.get("triggers", []),
                situation=mood_data.get("situation"),
                activity=mood_data.get("activity")
            ),
            intervention=MoodIntervention(
                technique=mood_data.get("technique"),
                exercises=mood_data.get("exercises", [])
            ),
            conversation_id=conversation_id,
            message_id=message_id
        )

        # Save to MongoDB
        await db.create_mood_entry(mood_entry)

        logger.info(f"😊 Saved mood entry: {mood_entry.mood.primary} ({mood_entry.mood.intensity}/10) for {user_id}")

        return entry_id

    async def get_mood_history(
        self,
        user_id: str,
        days: int = 7
    ) -> List[Dict]:
        """
        Get mood history for user

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            List of mood entries
        """
        db = self._get_db()
        if not db:
            return []

        entries = await db.get_mood_entries(user_id, days=days)

        return [
            {
                "timestamp": entry.timestamp.isoformat(),
                "mood": entry.mood.primary,
                "intensity": entry.mood.intensity,
                "description": entry.mood.description,
                "triggers": entry.context.triggers,
                "situation": entry.context.situation
            }
            for entry in entries
        ]

    async def get_mood_statistics(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get mood statistics for user

        Args:
            user_id: User ID
            days: Number of days to analyze

        Returns:
            Dict with statistics
        """
        db = self._get_db()
        if not db:
            return {}

        return await db.get_mood_statistics(user_id, days=days)
