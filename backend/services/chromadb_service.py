"""
ChromaDB Service - Semantic Memory & Vector Search dla LumenAI

ChromaDB przechowuje embeddings (wektory) wiadomości, co pozwala na:
- Semantyczne wyszukiwanie ("znajdź rozmowy o pracy")
- Rekomendacje podobnych rozmów
- Grupowanie tematyczne
- Kontekst z przeszłych rozmów

Architektura:
1. Każda wiadomość → embedding (1536-wymiarowy wektor)
2. ChromaDB przechowuje embedding + metadata
3. Wyszukiwanie przez similarity search
"""

import chromadb
try:
    from chromadb.config import Settings
except ImportError:
    # ChromaDB 0.5+ uses Settings from main module
    from chromadb import Settings
from typing import List, Dict, Optional, Any
from datetime import datetime
from loguru import logger
import hashlib


class ChromaDBService:
    """
    Service do zarządzania embeddings i semantic search.

    Collections:
    - lumenai_messages: Wszystkie wiadomości użytkowników
    - lumenai_conversations: Podsumowania rozmów
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8001,
        collection_name: str = "lumenai_messages"
    ):
        """
        Inicjalizacja ChromaDB.

        Args:
            host: Host ChromaDB (default: localhost)
            port: Port ChromaDB (default: 8001)
            collection_name: Nazwa kolekcji (default: lumenai_messages)
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.client: Optional[chromadb.HttpClient] = None
        self.collection = None

    async def connect(self):
        """Połącz z ChromaDB"""
        try:
            # ChromaDB HTTP Client
            self.client = chromadb.HttpClient(
                host=self.host,
                port=self.port,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Testuj połączenie
            self.client.heartbeat()

            # Pobierz lub utwórz kolekcję
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "LumenAI message embeddings for semantic search"}
            )

            logger.info(f"✅ ChromaDB connected: {self.host}:{self.port}")
            logger.info(f"📚 Collection '{self.collection_name}' ready ({self.collection.count()} documents)")
            return True

        except Exception as e:
            logger.warning(f"⚠️  ChromaDB connection failed: {e}")
            logger.warning("🔄 Running without vector search capabilities")
            return False

    async def disconnect(self):
        """Rozłącz z ChromaDB"""
        if self.client:
            self.client = None
            logger.info("ChromaDB disconnected")

    async def health_check(self) -> bool:
        """Sprawdź czy ChromaDB działa"""
        try:
            if self.client:
                self.client.heartbeat()
                return True
        except:
            pass
        return False

    async def add_message(
        self,
        message_id: str,
        user_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Dodaj wiadomość z embeddingiem do ChromaDB.

        Args:
            message_id: Unikalny ID wiadomości
            user_id: ID użytkownika
            content: Treść wiadomości
            embedding: Wektor embedding (1536-wymiarowy dla OpenAI)
            metadata: Dodatkowe metadane (timestamp, agent, conversation_id, etc.)

        Returns:
            True jeśli sukces, False jeśli błąd
        """
        if not self.collection:
            logger.warning("ChromaDB not connected, skipping embedding storage")
            return False

        try:
            # Przygotuj metadane
            meta = metadata or {}
            meta.update({
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "content_length": len(content)
            })

            # Dodaj do ChromaDB
            self.collection.add(
                ids=[message_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[meta]
            )

            logger.debug(f"📝 Added message {message_id} to ChromaDB")
            return True

        except Exception as e:
            logger.error(f"Failed to add message to ChromaDB: {e}")
            return False

    async def search_similar(
        self,
        query_embedding: List[float],
        user_id: Optional[str] = None,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Wyszukaj podobne wiadomości używając similarity search.

        Args:
            query_embedding: Embedding zapytania
            user_id: Opcjonalnie filtruj po user_id
            n_results: Ile wyników zwrócić
            where: Dodatkowe filtry (np. {"agent": "mood"})

        Returns:
            Lista podobnych wiadomości z metadanymi i dystansem
        """
        if not self.collection:
            logger.warning("ChromaDB not connected")
            return []

        try:
            # Przygotuj filtry
            where_filter = where or {}
            if user_id:
                where_filter["user_id"] = user_id

            # Wyszukaj
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter if where_filter else None,
                include=["documents", "metadatas", "distances"]
            )

            # Formatuj wyniki
            formatted = []
            if results and results["ids"]:
                for i, doc_id in enumerate(results["ids"][0]):
                    formatted.append({
                        "id": doc_id,
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i],
                        "similarity": 1 - results["distances"][0][i]  # Convert distance to similarity
                    })

            logger.debug(f"🔍 Found {len(formatted)} similar messages")
            return formatted

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def search_by_text(
        self,
        query_text: str,
        user_id: Optional[str] = None,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Wyszukaj podobne wiadomości używając tekstu (bez ręcznego embeddingu).

        UWAGA: Ta metoda wymaga wygenerowania embeddingu dla query_text
        najpierw przez OpenAI API. Użyj search_similar() zamiast tego.

        Args:
            query_text: Tekst zapytania
            user_id: Opcjonalnie filtruj po user_id
            n_results: Ile wyników zwrócić

        Returns:
            Lista podobnych wiadomości
        """
        # To będzie zaimplementowane po dodaniu embedding service
        logger.warning("search_by_text requires embedding service - use search_similar instead")
        return []

    async def get_conversation_context(
        self,
        user_id: str,
        query_embedding: List[float],
        n_results: int = 5
    ) -> str:
        """
        Pobierz kontekst z podobnych przeszłych rozmów.

        Użyj tego aby dać LLM kontekst z przeszłości:
        "Użytkownik wcześniej rozmawiał o podobnych tematach..."

        Args:
            user_id: ID użytkownika
            query_embedding: Embedding obecnej wiadomości
            n_results: Ile kontekstów zwrócić

        Returns:
            Sformatowany string z kontekstem
        """
        similar = await self.search_similar(
            query_embedding=query_embedding,
            user_id=user_id,
            n_results=n_results
        )

        if not similar:
            return "No similar past conversations found."

        # Formatuj kontekst
        context_parts = []
        for item in similar:
            context_parts.append(
                f"[{item['metadata'].get('timestamp', 'unknown')}] "
                f"{item['content'][:100]}... (similarity: {item['similarity']:.2f})"
            )

        return "Similar past conversations:\n" + "\n".join(context_parts)

    async def delete_user_data(self, user_id: str) -> bool:
        """
        Usuń wszystkie embeddingi użytkownika (GDPR compliance).

        Args:
            user_id: ID użytkownika

        Returns:
            True jeśli sukces
        """
        if not self.collection:
            return False

        try:
            # Pobierz wszystkie ID użytkownika
            results = self.collection.get(
                where={"user_id": user_id},
                include=[]
            )

            if results and results["ids"]:
                self.collection.delete(ids=results["ids"])
                logger.info(f"🗑️  Deleted {len(results['ids'])} embeddings for user {user_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to delete user data: {e}")

        return False

    def get_stats(self) -> Dict[str, Any]:
        """Pobierz statystyki kolekcji"""
        if not self.collection:
            return {"status": "disconnected"}

        try:
            count = self.collection.count()
            return {
                "status": "connected",
                "collection": self.collection_name,
                "documents": count,
                "host": f"{self.host}:{self.port}"
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# ============================================================================
# Singleton Pattern - Jedna instancja dla całej aplikacji
# ============================================================================

_chromadb_service: Optional[ChromaDBService] = None


def init_chromadb_service(
    host: str = "localhost",
    port: int = 8001,
    collection_name: str = "lumenai_messages"
) -> ChromaDBService:
    """Inicjalizuj globalny ChromaDB service"""
    global _chromadb_service

    _chromadb_service = ChromaDBService(
        host=host,
        port=port,
        collection_name=collection_name
    )

    return _chromadb_service


def get_chromadb_service() -> Optional[ChromaDBService]:
    """Pobierz globalny ChromaDB service"""
    return _chromadb_service
