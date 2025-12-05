"""
MongoDB Service - Warstwa obsługi bazy danych

Ten plik to "mostek" między kodem Pythona a bazą danych MongoDB.
Zawiera wszystkie operacje na bazie: dodawanie, odczytywanie, aktualizowanie, usuwanie.

DLACZEGO TWORZYMY TO?
- Separacja logiki - kod nie musi wiedzieć JAK działa MongoDB
- Łatwe testowanie - możemy podmienić bazę na "fake" do testów
- Reużywalność - jedna metoda do zapisu używana wszędzie
- Bezpieczeństwo - wszystko przechodzi przez jedną warstwę
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from backend.models.database import (
    User, Conversation, Message, MoodEntry, UserContext,
    model_to_dict
)

logger = logging.getLogger(__name__)


class MongoDBService:
    """
    Serwis do obsługi MongoDB.

    Przykład użycia:
        # Inicjalizacja
        db_service = MongoDBService("mongodb://localhost:27017")
        await db_service.connect()

        # Zapis użytkownika
        user = User(user_id="user_123", profile={"name": "Marek"})
        await db_service.create_user(user)

        # Odczyt użytkownika
        user = await db_service.get_user("user_123")
    """

    def __init__(self, connection_string: str, database_name: str = "lumenai_db"):
        """
        Inicjalizacja serwisu MongoDB.

        Args:
            connection_string: URL MongoDB (np. "mongodb://localhost:27017")
            database_name: Nazwa bazy danych (domyślnie "lumenai_db")
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None

    # ========================================================================
    # POŁĄCZENIE Z BAZĄ
    # ========================================================================

    async def connect(self):
        """
        Nawiązuje połączenie z MongoDB.

        MUSISZ wywołać to przy starcie aplikacji!
        """
        try:
            logger.info(f"Łączenie z MongoDB: {self.connection_string}")
            # Add timeout to prevent hanging and connection pool limits
            self.client = AsyncIOMotorClient(
                self.connection_string,
                serverSelectionTimeoutMS=3000,  # 3 second timeout
                maxPoolSize=50,  # Maximum 50 connections in pool
                minPoolSize=10,  # Keep minimum 10 connections ready
                maxIdleTimeMS=45000,  # Close idle connections after 45 seconds
                waitQueueTimeoutMS=10000  # Wait max 10 seconds for connection from pool
            )
            self.db = self.client[self.database_name]

            # Test połączenia with timeout
            await self.client.admin.command('ping')
            logger.info(f"✅ Połączono z MongoDB! Baza: {self.database_name}")

            # Tworzenie indeksów (przyspieszają wyszukiwanie)
            await self._create_indexes()

        except Exception as e:
            logger.error(f"❌ Błąd połączenia z MongoDB: {e}")
            raise

    async def disconnect(self):
        """
        Zamyka połączenie z MongoDB.

        Wywołaj to przy wyłączaniu aplikacji.
        """
        if self.client:
            self.client.close()
            logger.info("Rozłączono z MongoDB")

    async def _create_indexes(self):
        """
        Tworzy indeksy w kolekcjach (przyspieszają zapytania).

        INDEKS to jak zakładka w książce - szybciej znajdziesz to czego szukasz.
        """
        try:
            # Users: indeks na user_id (unikalny)
            await self.db.users.create_index("user_id", unique=True)

            # Conversations: indeks na conversation_id (unikalny)
            await self.db.conversations.create_index("conversation_id", unique=True)
            # Conversations: indeks na user_id + started_at (szybkie wyszukiwanie rozmów użytkownika)
            await self.db.conversations.create_index([("user_id", 1), ("started_at", -1)])

            # Messages: indeks na message_id (unikalny)
            await self.db.messages.create_index("message_id", unique=True)
            # Messages: indeks na conversation_id + timestamp (chronologiczne wiadomości)
            await self.db.messages.create_index([("conversation_id", 1), ("timestamp", 1)])
            # Messages: indeks na user_id + timestamp (historia użytkownika)
            await self.db.messages.create_index([("user_id", 1), ("timestamp", -1)])

            # Mood Entries: indeks na entry_id (unikalny)
            await self.db.mood_entries.create_index("entry_id", unique=True)
            # Mood Entries: indeks na user_id + timestamp (chronologia nastrojów)
            await self.db.mood_entries.create_index([("user_id", 1), ("timestamp", -1)])

            # User Context: compound unique index na user_id + context_type + key
            await self.db.user_context.create_index(
                [("user_id", 1), ("context_type", 1), ("key", 1)],
                unique=True
            )

            logger.info("✅ Indeksy MongoDB utworzone")

        except Exception as e:
            logger.warning(f"⚠️  Błąd tworzenia indeksów (może już istnieją): {e}")

    # ========================================================================
    # OPERACJE NA UŻYTKOWNIKACH (USERS)
    # ========================================================================

    async def create_user(self, user: User) -> User:
        """
        Tworzy nowego użytkownika w bazie.

        Args:
            user: Obiekt User do zapisania

        Returns:
            Zapisany użytkownik (z wygenerowanym _id)

        Przykład:
            user = User(user_id="user_123")
            saved_user = await db_service.create_user(user)
        """
        user_dict = model_to_dict(user)
        result = await self.db.users.insert_one(user_dict)
        user_dict["_id"] = result.inserted_id
        logger.info(f"✅ Utworzono użytkownika: {user.user_id}")
        return User(**user_dict)

    async def get_user(self, user_id: str) -> Optional[User]:
        """
        Pobiera użytkownika po user_id.

        Args:
            user_id: ID użytkownika (np. "user_123")

        Returns:
            User jeśli znaleziono, None jeśli nie
        """
        user_dict = await self.db.users.find_one({"user_id": user_id})
        if user_dict:
            return User(**user_dict)
        return None

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Aktualizuje dane użytkownika.

        Args:
            user_id: ID użytkownika
            updates: Dict z polami do aktualizacji

        Returns:
            True jeśli zaktualizowano, False jeśli użytkownik nie istnieje

        Przykład:
            await db_service.update_user("user_123", {
                "profile.name": "Marek Kowalski",
                "updated_at": datetime.utcnow()
            })
        """
        updates["updated_at"] = datetime.utcnow()
        result = await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    async def increment_user_stats(self, user_id: str, conversations: int = 0, messages: int = 0):
        """
        Zwiększa statystyki użytkownika (liczniki).

        Args:
            user_id: ID użytkownika
            conversations: O ile zwiększyć licznik rozmów
            messages: O ile zwiększyć licznik wiadomości
        """
        increments = {}
        if conversations > 0:
            increments["metadata.total_conversations"] = conversations
        if messages > 0:
            increments["metadata.total_messages"] = messages

        if increments:
            await self.db.users.update_one(
                {"user_id": user_id},
                {
                    "$inc": increments,
                    "$set": {
                        "metadata.last_active": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )

    # ========================================================================
    # OPERACJE NA ROZMOWACH (CONVERSATIONS)
    # ========================================================================

    async def create_conversation(self, conversation: Conversation) -> Conversation:
        """
        Tworzy nową rozmowę.

        Args:
            conversation: Obiekt Conversation

        Returns:
            Zapisana rozmowa
        """
        conv_dict = model_to_dict(conversation)
        result = await self.db.conversations.insert_one(conv_dict)
        conv_dict["_id"] = result.inserted_id
        logger.info(f"✅ Utworzono rozmowę: {conversation.conversation_id}")

        # Zwiększ licznik rozmów użytkownika
        await self.increment_user_stats(conversation.user_id, conversations=1)

        return Conversation(**conv_dict)

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Pobiera rozmowę po ID."""
        conv_dict = await self.db.conversations.find_one({"conversation_id": conversation_id})
        if conv_dict:
            return Conversation(**conv_dict)
        return None

    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = 20,
        skip: int = 0,
        status: str = "active"
    ) -> List[Conversation]:
        """
        Pobiera rozmowy użytkownika (najnowsze na początku).

        Args:
            user_id: ID użytkownika
            limit: Ile rozmów pobrać (domyślnie 20)
            skip: Ile rozmów pominąć (do paginacji)
            status: Status rozmowy ("active" lub "archived")

        Returns:
            Lista rozmów
        """
        query = {"user_id": user_id}
        if status:
            query["status"] = status

        cursor = self.db.conversations.find(query).sort("last_message_at", -1).skip(skip).limit(limit)
        conversations = await cursor.to_list(length=limit)
        return [Conversation(**conv) for conv in conversations]

    async def update_conversation(self, conversation_id: str, updates: Dict[str, Any]) -> bool:
        """
        Aktualizuje rozmowę.

        Często używane do:
        - Aktualizacji last_message_at
        - Zwiększenia message_count
        - Dodania agenta do agents_used
        """
        result = await self.db.conversations.update_one(
            {"conversation_id": conversation_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    async def add_agent_to_conversation(self, conversation_id: str, agent: str):
        """
        Dodaje agenta do listy użytych agentów w rozmowie.

        Args:
            conversation_id: ID rozmowy
            agent: Nazwa agenta (np. "planner", "mood")
        """
        # $addToSet dodaje tylko jeśli jeszcze nie ma (nie duplikuje)
        await self.db.conversations.update_one(
            {"conversation_id": conversation_id},
            {
                "$addToSet": {"agents_used": agent},
                "$set": {"last_message_at": datetime.utcnow()}
            }
        )

    async def increment_message_count(self, conversation_id: str):
        """Zwiększa licznik wiadomości w rozmowie."""
        await self.db.conversations.update_one(
            {"conversation_id": conversation_id},
            {
                "$inc": {"message_count": 1},
                "$set": {"last_message_at": datetime.utcnow()}
            }
        )

    # ========================================================================
    # OPERACJE NA WIADOMOŚCIACH (MESSAGES)
    # ========================================================================

    async def create_message(self, message: Message) -> Message:
        """
        Zapisuje wiadomość do bazy.

        Args:
            message: Obiekt Message

        Returns:
            Zapisana wiadomość

        UWAGA: Automatycznie aktualizuje conversation i statystyki użytkownika!
        """
        msg_dict = model_to_dict(message)
        result = await self.db.messages.insert_one(msg_dict)
        msg_dict["_id"] = result.inserted_id
        logger.debug(f"💬 Zapisano wiadomość: {message.message_id}")

        # Aktualizuj rozmowę
        await self.increment_message_count(message.conversation_id)

        # Zwiększ licznik wiadomości użytkownika
        await self.increment_user_stats(message.user_id, messages=1)

        # Jeśli wiadomość od agenta, dodaj go do listy
        if message.agent:
            await self.add_agent_to_conversation(message.conversation_id, message.agent)

        return Message(**msg_dict)

    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        Pobiera wszystkie wiadomości z rozmowy (chronologicznie).

        Args:
            conversation_id: ID rozmowy
            limit: Ograniczenie liczby wiadomości (None = wszystkie)

        Returns:
            Lista wiadomości (od najstarszej do najnowszej)
        """
        cursor = self.db.messages.find({"conversation_id": conversation_id}).sort("timestamp", 1)

        if limit:
            cursor = cursor.limit(limit)

        messages = await cursor.to_list(length=None)
        return [Message(**msg) for msg in messages]

    async def get_recent_messages(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Message]:
        """
        Pobiera ostatnie wiadomości użytkownika (z wszystkich rozmów).

        Args:
            user_id: ID użytkownika
            limit: Ile wiadomości pobrać

        Returns:
            Lista wiadomości (najnowsze na początku)
        """
        cursor = self.db.messages.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
        messages = await cursor.to_list(length=limit)
        return [Message(**msg) for msg in messages]

    # ========================================================================
    # OPERACJE NA WPISACH NASTROJÓW (MOOD ENTRIES)
    # ========================================================================

    async def create_mood_entry(self, mood_entry: MoodEntry) -> MoodEntry:
        """
        Zapisuje wpis nastroju.

        Args:
            mood_entry: Obiekt MoodEntry

        Returns:
            Zapisany wpis
        """
        entry_dict = model_to_dict(mood_entry)
        result = await self.db.mood_entries.insert_one(entry_dict)
        entry_dict["_id"] = result.inserted_id
        logger.info(f"😊 Zapisano wpis nastroju: {mood_entry.mood.primary} ({mood_entry.mood.intensity}/10)")
        return MoodEntry(**entry_dict)

    async def get_mood_entries(
        self,
        user_id: str,
        days: int = 7,
        limit: Optional[int] = None
    ) -> List[MoodEntry]:
        """
        Pobiera wpisy nastrojów z ostatnich X dni.

        Args:
            user_id: ID użytkownika
            days: Ile dni wstecz (domyślnie 7)
            limit: Maksymalna liczba wpisów

        Returns:
            Lista wpisów (chronologicznie)
        """
        since = datetime.utcnow() - timedelta(days=days)
        query = {
            "user_id": user_id,
            "timestamp": {"$gte": since}
        }

        cursor = self.db.mood_entries.find(query).sort("timestamp", 1)

        if limit:
            cursor = cursor.limit(limit)

        entries = await cursor.to_list(length=None)
        return [MoodEntry(**entry) for entry in entries]

    async def get_mood_statistics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Oblicza statystyki nastrojów użytkownika.

        Args:
            user_id: ID użytkownika
            days: Za ile dni obliczyć statystyki

        Returns:
            Dict ze statystykami:
            - average_intensity: Średnia intensywność
            - most_common_mood: Najczęstszy nastrój
            - mood_distribution: Rozkład nastrojów
            - total_entries: Liczba wpisów
        """
        entries = await self.get_mood_entries(user_id, days=days)

        if not entries:
            return {
                "average_intensity": None,
                "most_common_mood": None,
                "mood_distribution": {},
                "total_entries": 0
            }

        # Oblicz średnią intensywność
        avg_intensity = sum(e.mood.intensity for e in entries) / len(entries)

        # Policz wystąpienia każdego nastroju
        mood_counts = {}
        for entry in entries:
            mood = entry.mood.primary
            mood_counts[mood] = mood_counts.get(mood, 0) + 1

        # Najczęstszy nastrój
        most_common = max(mood_counts.items(), key=lambda x: x[1])[0]

        return {
            "average_intensity": round(avg_intensity, 2),
            "most_common_mood": most_common,
            "mood_distribution": mood_counts,
            "total_entries": len(entries)
        }

    # ========================================================================
    # OPERACJE NA KONTEKŚCIE UŻYTKOWNIKA (USER CONTEXT)
    # ========================================================================

    async def upsert_user_context(
        self,
        user_id: str,
        context_type: str,
        key: str,
        value: Any,
        confidence: float = 1.0,
        source: str = "conversation",
        conversation_id: Optional[str] = None
    ) -> UserContext:
        """
        Zapisuje lub aktualizuje kontekst użytkownika.

        UPSERT = UPDATE + INSERT:
        - Jeśli kontekst istnieje → aktualizuj
        - Jeśli nie istnieje → utwórz nowy

        Args:
            user_id: ID użytkownika
            context_type: Typ kontekstu (personal_info/goals/habits/etc)
            key: Klucz (np. "job", "hobby")
            value: Wartość
            confidence: Pewność (0-1)
            source: Źródło (conversation/user_input/inferred)
            conversation_id: ID rozmowy z której pochodzi

        Returns:
            Zapisany lub zaktualizowany kontekst
        """
        existing = await self.db.user_context.find_one({
            "user_id": user_id,
            "context_type": context_type,
            "key": key
        })

        if existing:
            # Aktualizuj istniejący
            updates = {
                "value": value,
                "confidence": max(confidence, existing.get("confidence", 0)),  # Wyższa pewność
                "last_updated": datetime.utcnow(),
                "mention_count": existing.get("mention_count", 0) + 1
            }

            if conversation_id and conversation_id not in existing.get("related_conversations", []):
                await self.db.user_context.update_one(
                    {"_id": existing["_id"]},
                    {
                        "$set": updates,
                        "$addToSet": {"related_conversations": conversation_id}
                    }
                )
            else:
                await self.db.user_context.update_one(
                    {"_id": existing["_id"]},
                    {"$set": updates}
                )

            updated = await self.db.user_context.find_one({"_id": existing["_id"]})
            return UserContext(**updated)

        else:
            # Utwórz nowy
            context = UserContext(
                user_id=user_id,
                context_type=context_type,
                key=key,
                value=value,
                confidence=confidence,
                source=source,
                related_conversations=[conversation_id] if conversation_id else []
            )
            ctx_dict = model_to_dict(context)
            result = await self.db.user_context.insert_one(ctx_dict)
            ctx_dict["_id"] = result.inserted_id
            logger.info(f"💡 Nowy kontekst: {context_type}.{key} = {value}")
            return UserContext(**ctx_dict)

    async def get_user_context(
        self,
        user_id: str,
        context_type: Optional[str] = None,
        min_confidence: float = 0.0
    ) -> List[UserContext]:
        """
        Pobiera kontekst użytkownika.

        Args:
            user_id: ID użytkownika
            context_type: Opcjonalnie filtruj po typie
            min_confidence: Minimalna pewność (0-1)

        Returns:
            Lista kontekstów
        """
        query = {
            "user_id": user_id,
            "confidence": {"$gte": min_confidence}
        }

        if context_type:
            query["context_type"] = context_type

        cursor = self.db.user_context.find(query).sort("confidence", -1)
        contexts = await cursor.to_list(length=None)
        return [UserContext(**ctx) for ctx in contexts]

    async def delete_user_context(self, user_id: str, context_type: str, key: str) -> bool:
        """
        Usuwa pojedynczy kontekst użytkownika.

        Returns:
            True jeśli usunięto, False jeśli nie znaleziono
        """
        result = await self.db.user_context.delete_one({
            "user_id": user_id,
            "context_type": context_type,
            "key": key
        })
        return result.deleted_count > 0

    # ========================================================================
    # POMOCNICZE METODY
    # ========================================================================

    async def health_check(self) -> bool:
        """
        Sprawdza czy połączenie z MongoDB działa.

        Returns:
            True jeśli OK, False jeśli problem
        """
        try:
            await self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False

    async def get_database_stats(self) -> Dict[str, Any]:
        """
        Pobiera statystyki bazy danych.

        Returns:
            Dict ze statystykami (rozmiar, liczba dokumentów, etc.)
        """
        try:
            stats = await self.db.command("dbStats")
            return {
                "database": self.database_name,
                "collections": stats.get("collections", 0),
                "objects": stats.get("objects", 0),
                "dataSize": stats.get("dataSize", 0),
                "indexSize": stats.get("indexSize", 0)
            }
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}


# ============================================================================
# SINGLETON INSTANCE - Globalna instancja serwisu
# ============================================================================

_mongodb_service: Optional[MongoDBService] = None


def get_mongodb_service() -> MongoDBService:
    """
    Zwraca globalną instancję MongoDB service.

    Użyj tego w innych plikach:
        from services.mongodb_service import get_mongodb_service
        db = get_mongodb_service()
        user = await db.get_user("user_123")
    """
    if _mongodb_service is None:
        raise RuntimeError("MongoDB service not initialized! Call init_mongodb_service() first.")
    return _mongodb_service


def init_mongodb_service(connection_string: str, database_name: str = "lumenai_db") -> MongoDBService:
    """
    Inicjalizuje globalną instancję MongoDB service.

    Wywołaj to RAZ przy starcie aplikacji!

    Args:
        connection_string: URL MongoDB
        database_name: Nazwa bazy danych

    Returns:
        Zainicjalizowana instancja serwisu
    """
    global _mongodb_service
    _mongodb_service = MongoDBService(connection_string, database_name)
    return _mongodb_service
