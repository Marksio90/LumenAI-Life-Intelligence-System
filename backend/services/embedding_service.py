"""
Embedding Service - Generowanie wektorów dla semantycznego wyszukiwania

Używa OpenAI Embeddings API do konwersji tekstu na wektory.

Model: text-embedding-3-small (1536 wymiarów)
- Tańszy i szybszy niż text-embedding-3-large
- Doskonała jakość dla większości zastosowań
- ~0.00002$ za 1000 tokenów

Koszt przykładowy:
- 1000 wiadomości x 50 tokenów = 50,000 tokenów = $0.001
"""

from openai import AsyncOpenAI
from typing import List, Optional, Union
from loguru import logger
import hashlib
import json


class EmbeddingService:
    """
    Service do generowania embeddings.

    Przykład użycia:
        service = EmbeddingService(api_key="sk-...")
        embedding = await service.generate("Hello world")
        print(len(embedding))  # 1536
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        cache_enabled: bool = True
    ):
        """
        Inicjalizacja Embedding Service.

        Args:
            api_key: OpenAI API key
            model: Model embeddingów (default: text-embedding-3-small)
            cache_enabled: Czy cachować embeddingi (oszczędza API calls)
        """
        self.api_key = api_key
        self.model = model
        self.cache_enabled = cache_enabled
        self.client = AsyncOpenAI(api_key=api_key)

        # Cache embeddings (hash tekstu -> embedding)
        self._cache: dict = {}

        logger.info(f"🧮 Embedding Service initialized: {model}")

    def _get_cache_key(self, text: str) -> str:
        """Wygeneruj cache key z tekstu"""
        return hashlib.md5(text.encode()).hexdigest()

    async def generate(
        self,
        text: str,
        use_cache: bool = True
    ) -> List[float]:
        """
        Wygeneruj embedding dla tekstu.

        Args:
            text: Tekst do embeddingu
            use_cache: Czy użyć cache (default: True)

        Returns:
            Lista float (1536 wymiarów dla text-embedding-3-small)
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return [0.0] * 1536  # Return zero vector

        # Sprawdź cache
        if use_cache and self.cache_enabled:
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                logger.debug(f"📦 Using cached embedding for: {text[:30]}...")
                return self._cache[cache_key]

        try:
            # Wygeneruj embedding przez OpenAI API
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )

            embedding = response.data[0].embedding

            # Cachuj
            if use_cache and self.cache_enabled:
                cache_key = self._get_cache_key(text)
                self._cache[cache_key] = embedding

            logger.debug(f"✨ Generated embedding: {len(embedding)} dims for {len(text)} chars")
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Zwróć zero vector jako fallback
            return [0.0] * 1536

    async def generate_batch(
        self,
        texts: List[str],
        use_cache: bool = True
    ) -> List[List[float]]:
        """
        Wygeneruj embeddingi dla wielu tekstów naraz (batch).

        BATCH = TANIEJ! OpenAI API pozwala na batch requests.

        Args:
            texts: Lista tekstów
            use_cache: Czy użyć cache

        Returns:
            Lista embeddingów (każdy 1536 wymiarów)
        """
        if not texts:
            return []

        results = []
        uncached_texts = []
        uncached_indices = []

        # Sprawdź co jest w cache
        for i, text in enumerate(texts):
            if use_cache and self.cache_enabled:
                cache_key = self._get_cache_key(text)
                if cache_key in self._cache:
                    results.append(self._cache[cache_key])
                    continue

            # Nie ma w cache
            uncached_texts.append(text)
            uncached_indices.append(i)
            results.append(None)  # Placeholder

        # Wygeneruj brakujące embeddingi
        if uncached_texts:
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=uncached_texts,
                    encoding_format="float"
                )

                # Wypełnij wyniki
                for i, embedding_data in enumerate(response.data):
                    embedding = embedding_data.embedding
                    original_idx = uncached_indices[i]
                    results[original_idx] = embedding

                    # Cachuj
                    if use_cache and self.cache_enabled:
                        cache_key = self._get_cache_key(uncached_texts[i])
                        self._cache[cache_key] = embedding

                logger.info(f"✨ Generated {len(uncached_texts)} embeddings in batch")

            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                # Wypełnij zero vectors
                for idx in uncached_indices:
                    results[idx] = [0.0] * 1536

        return results

    async def calculate_similarity(
        self,
        text1: str,
        text2: str
    ) -> float:
        """
        Oblicz podobieństwo semantyczne między dwoma tekstami.

        Returns:
            Float 0.0-1.0 (0 = różne, 1 = identyczne)
        """
        embedding1 = await self.generate(text1)
        embedding2 = await self.generate(text2)

        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        similarity = dot_product / (magnitude1 * magnitude2)
        return max(0.0, min(1.0, similarity))  # Clip to 0-1

    def clear_cache(self):
        """Wyczyść cache embeddings"""
        self._cache.clear()
        logger.info("🗑️  Embedding cache cleared")

    def get_cache_stats(self) -> dict:
        """Pobierz statystyki cache"""
        return {
            "cached_embeddings": len(self._cache),
            "model": self.model,
            "cache_enabled": self.cache_enabled
        }


# ============================================================================
# Singleton Pattern
# ============================================================================

_embedding_service: Optional[EmbeddingService] = None


def init_embedding_service(
    api_key: str,
    model: str = "text-embedding-3-small"
) -> EmbeddingService:
    """Inicjalizuj globalny Embedding Service"""
    global _embedding_service

    _embedding_service = EmbeddingService(
        api_key=api_key,
        model=model
    )

    return _embedding_service


def get_embedding_service() -> Optional[EmbeddingService]:
    """Pobierz globalny Embedding Service"""
    return _embedding_service
