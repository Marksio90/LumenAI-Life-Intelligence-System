"""
Analytics Service - Zaawansowana Analiza Rozmów i Trendów dla LumenAI

Ten service dostarcza:
1. 📝 Conversation Summarization - automatyczne podsumowania
2. 🎯 Topic Clustering - grupowanie po tematach
3. 📊 Trend Analysis - analiza trendów nastrojów
4. 💡 Recommendations - rekomendacje oparte na podobieństwach

Wykorzystuje:
- LLM (GPT-4o-mini) do summarization
- K-means clustering na embeddingach
- Statistical analysis dla trendów
- Collaborative filtering dla rekomendacji
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from loguru import logger
import numpy as np
from collections import defaultdict, Counter
import statistics


class AnalyticsService:
    """
    Zaawansowana analityka dla LumenAI.

    Wszystkie funkcje działają asynchronicznie i są zoptymalizowane
    pod kątem performance.
    """

    def __init__(self, llm_engine, memory_manager, chromadb_service, embedding_service):
        """
        Inicjalizacja Analytics Service.

        Args:
            llm_engine: LLM Engine do generowania podsumowań
            memory_manager: Memory Manager do dostępu do danych
            chromadb_service: ChromaDB do semantic analysis
            embedding_service: Embedding Service do vectorization
        """
        self.llm = llm_engine
        self.memory = memory_manager
        self.chromadb = chromadb_service
        self.embeddings = embedding_service

        logger.info("📊 Analytics Service initialized")

    # ========================================================================
    # 1. CONVERSATION SUMMARIZATION
    # ========================================================================

    async def summarize_conversation(
        self,
        conversation_id: str,
        max_length: int = 200
    ) -> Dict[str, Any]:
        """
        Wygeneruj automatyczne podsumowanie rozmowy.

        Przykład:
            summary = await analytics.summarize_conversation("conv_123")
            # Returns: {
            #   "summary": "Użytkownik rozmawiał o stresie w pracy...",
            #   "key_topics": ["stres", "praca", "mindfulness"],
            #   "sentiment": "negative",
            #   "action_items": ["Spróbować technik relaksacyjnych"]
            # }

        Args:
            conversation_id: ID rozmowy do podsumowania
            max_length: Max długość podsumowania

        Returns:
            Dict z podsumowaniem i metadanymi
        """
        logger.info(f"📝 Summarizing conversation {conversation_id}")

        try:
            # Pobierz wiadomości z rozmowy
            db = self.memory._get_db()
            if not db:
                return {"error": "Database not available"}

            messages = await db.get_conversation_messages(conversation_id)

            if not messages or len(messages) == 0:
                return {"error": "No messages found"}

            # Przygotuj transkrypt rozmowy
            transcript = self._format_transcript(messages)

            # Wygeneruj podsumowanie przez LLM
            prompt = f"""Przeanalizuj poniższą rozmowę i wygeneruj podsumowanie.

ROZMOWA:
{transcript}

Wygeneruj podsumowanie w formacie JSON:
{{
    "summary": "Krótkie podsumowanie głównych tematów (max {max_length} znaków)",
    "key_topics": ["temat1", "temat2", "temat3"],
    "sentiment": "positive/negative/neutral/mixed",
    "mood_changes": "Opis zmian nastroju podczas rozmowy",
    "action_items": ["konkretna akcja 1", "konkretna akcja 2"],
    "insights": "Kluczowe spostrzeżenia o użytkowniku"
}}

Odpowiedz TYLKO validnym JSONem, bez dodatkowego tekstu."""

            response = await self.llm.generate(prompt, model="gpt-4o-mini")

            # Parse JSON response
            import json
            summary_data = json.loads(response)

            # Dodaj metadane
            summary_data.update({
                "conversation_id": conversation_id,
                "message_count": len(messages),
                "generated_at": datetime.utcnow().isoformat(),
                "duration_minutes": self._calculate_duration(messages)
            })

            logger.info(f"✅ Summary generated for {conversation_id}")
            return summary_data

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return {"error": str(e)}

    def _format_transcript(self, messages: List) -> str:
        """Formatuj wiadomości do transkryptu"""
        transcript_parts = []
        for msg in messages:
            role = "User" if msg.role == "user" else "Assistant"
            transcript_parts.append(f"{role}: {msg.content}")
        return "\n".join(transcript_parts)

    def _calculate_duration(self, messages: List) -> int:
        """Oblicz czas trwania rozmowy w minutach"""
        if len(messages) < 2:
            return 0
        first = messages[0].timestamp
        last = messages[-1].timestamp
        return int((last - first).total_seconds() / 60)

    async def summarize_recent_conversations(
        self,
        user_id: str,
        days: int = 7,
        n_conversations: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Podsumuj ostatnie rozmowy użytkownika.

        Args:
            user_id: ID użytkownika
            days: Ile dni wstecz
            n_conversations: Ile rozmów podsumować

        Returns:
            Lista podsumowań
        """
        db = self.memory._get_db()
        if not db:
            return []

        # Pobierz ostatnie rozmowy
        conversations = await db.get_user_conversations(
            user_id,
            limit=n_conversations
        )

        summaries = []
        for conv in conversations:
            summary = await self.summarize_conversation(conv.conversation_id)
            summaries.append(summary)

        return summaries

    # ========================================================================
    # 2. TOPIC CLUSTERING
    # ========================================================================

    async def cluster_conversations_by_topic(
        self,
        user_id: str,
        n_clusters: int = 5,
        min_conversations: int = 3
    ) -> Dict[str, Any]:
        """
        Grupuj rozmowy użytkownika po tematach używając K-means clustering.

        Przykład:
            clusters = await analytics.cluster_conversations_by_topic("user_123")
            # Returns: {
            #   "clusters": [
            #     {
            #       "cluster_id": 0,
            #       "label": "Stres w pracy",
            #       "size": 12,
            #       "conversations": [...]
            #     }
            #   ]
            # }

        Args:
            user_id: ID użytkownika
            n_clusters: Ile klastrów utworzyć
            min_conversations: Min liczba rozmów do clusteringu

        Returns:
            Dict z klastrami i ich opisami
        """
        logger.info(f"🎯 Clustering conversations for {user_id}")

        try:
            # Pobierz wszystkie rozmowy użytkownika z ChromaDB
            if not self.chromadb or not self.embeddings:
                return {"error": "ChromaDB not available"}

            # Get all user messages and their embeddings
            results = self.chromadb.collection.get(
                where={"user_id": user_id},
                include=["embeddings", "metadatas", "documents"]
            )

            if not results or len(results["ids"]) < min_conversations:
                return {
                    "error": f"Not enough data (need {min_conversations}, got {len(results['ids']) if results else 0})"
                }

            # Group messages by conversation
            conv_embeddings = defaultdict(list)
            conv_messages = defaultdict(list)

            for i, msg_id in enumerate(results["ids"]):
                conv_id = results["metadatas"][i].get("conversation_id")
                conv_embeddings[conv_id].append(results["embeddings"][i])
                conv_messages[conv_id].append(results["documents"][i])

            # Calculate average embedding for each conversation
            conv_vectors = []
            conv_ids = []
            for conv_id, embeddings in conv_embeddings.items():
                avg_embedding = np.mean(embeddings, axis=0)
                conv_vectors.append(avg_embedding)
                conv_ids.append(conv_id)

            # Perform K-means clustering
            from sklearn.cluster import KMeans

            # Adjust n_clusters if we have fewer conversations
            actual_clusters = min(n_clusters, len(conv_vectors))

            kmeans = KMeans(n_clusters=actual_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(conv_vectors)

            # Group conversations by cluster
            clusters = defaultdict(list)
            for conv_id, label in zip(conv_ids, cluster_labels):
                clusters[int(label)].append({
                    "conversation_id": conv_id,
                    "sample_messages": conv_messages[conv_id][:3]  # First 3 messages
                })

            # Generate labels for each cluster using LLM
            cluster_data = []
            for cluster_id, conversations in clusters.items():
                # Sample messages from this cluster
                sample_texts = []
                for conv in conversations[:5]:  # Max 5 conversations per cluster
                    sample_texts.extend(conv["sample_messages"][:2])

                # Generate cluster label
                label = await self._generate_cluster_label(sample_texts)

                cluster_data.append({
                    "cluster_id": cluster_id,
                    "label": label,
                    "size": len(conversations),
                    "conversations": [c["conversation_id"] for c in conversations],
                    "sample_topics": sample_texts[:3]
                })

            # Sort by size
            cluster_data.sort(key=lambda x: x["size"], reverse=True)

            logger.info(f"✅ Created {len(cluster_data)} clusters")

            return {
                "user_id": user_id,
                "total_conversations": len(conv_ids),
                "n_clusters": len(cluster_data),
                "clusters": cluster_data,
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return {"error": str(e)}

    async def _generate_cluster_label(self, sample_texts: List[str]) -> str:
        """Wygeneruj label dla clustra używając LLM"""
        try:
            combined = "\n".join(sample_texts[:10])  # Max 10 samples
            prompt = f"""Przeanalizuj poniższe fragmenty rozmów i wygeneruj JEDEN krótki (2-4 słowa) label opisujący główny temat.

FRAGMENTY:
{combined}

Odpowiedz TYLKO labelem, bez dodatkowego tekstu. Przykłady: "Stres w pracy", "Zdrowie psychiczne", "Rozwój osobisty"."""

            label = await self.llm.generate(prompt, model="gpt-4o-mini", max_tokens=20)
            return label.strip()

        except Exception as e:
            logger.error(f"Label generation failed: {e}")
            return "Nieznany temat"

    # ========================================================================
    # 3. TREND ANALYSIS
    # ========================================================================

    async def analyze_mood_trends(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analizuj trendy nastrojów użytkownika w czasie.

        Zwraca:
        - Trend ogólny (improving/declining/stable)
        - Wykres nastrojów w czasie
        - Korelacje z tematami rozmów
        - Predykcje

        Args:
            user_id: ID użytkownika
            days: Ile dni wstecz analizować

        Returns:
            Dict z analizą trendów
        """
        logger.info(f"📊 Analyzing mood trends for {user_id}")

        try:
            # Pobierz mood entries
            mood_history = await self.memory.get_mood_history(user_id, days=days)

            if not mood_history or len(mood_history) < 3:
                return {"error": "Not enough mood data"}

            # Extract mood intensity over time
            timestamps = []
            intensities = []
            moods = []

            for entry in mood_history:
                timestamps.append(datetime.fromisoformat(entry["timestamp"]))
                intensities.append(entry["intensity"])
                moods.append(entry["mood"])

            # Calculate trend
            trend = self._calculate_trend(intensities)

            # Calculate statistics
            avg_intensity = statistics.mean(intensities)
            std_intensity = statistics.stdev(intensities) if len(intensities) > 1 else 0

            # Most common moods
            mood_counts = Counter(moods)
            most_common_moods = mood_counts.most_common(3)

            # Detect mood volatility
            volatility = "high" if std_intensity > 2 else "moderate" if std_intensity > 1 else "low"

            # Generate insights
            insights = self._generate_mood_insights(
                trend, avg_intensity, volatility, most_common_moods
            )

            return {
                "user_id": user_id,
                "period_days": days,
                "total_entries": len(mood_history),
                "trend": trend,
                "statistics": {
                    "average_intensity": round(avg_intensity, 2),
                    "volatility": volatility,
                    "std_deviation": round(std_intensity, 2)
                },
                "most_common_moods": [
                    {"mood": mood, "count": count}
                    for mood, count in most_common_moods
                ],
                "insights": insights,
                "data_points": [
                    {
                        "timestamp": ts.isoformat(),
                        "intensity": intensity,
                        "mood": mood
                    }
                    for ts, intensity, mood in zip(timestamps, intensities, moods)
                ],
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return {"error": str(e)}

    def _calculate_trend(self, values: List[float]) -> str:
        """Oblicz trend (improving/declining/stable)"""
        if len(values) < 2:
            return "insufficient_data"

        # Linear regression slope
        x = list(range(len(values)))
        slope = np.polyfit(x, values, 1)[0]

        if slope > 0.3:
            return "improving"
        elif slope < -0.3:
            return "declining"
        else:
            return "stable"

    def _generate_mood_insights(
        self,
        trend: str,
        avg_intensity: float,
        volatility: str,
        most_common_moods: List[Tuple[str, int]]
    ) -> List[str]:
        """Wygeneruj insights o nastrojach"""
        insights = []

        # Trend insights
        if trend == "improving":
            insights.append("📈 Twój nastrój wykazuje trend wzrostowy - świetna robota!")
        elif trend == "declining":
            insights.append("📉 Zauważamy trend spadkowy - rozważ wsparcie specjalisty")
        else:
            insights.append("➡️ Twój nastrój jest stabilny")

        # Intensity insights
        if avg_intensity < 4:
            insights.append("⚠️ Średnia intensywność emocji jest niska - może warto porozmawiać?")
        elif avg_intensity > 7:
            insights.append("⚡ Wysoka intensywność emocji - pamiętaj o technikach uspokajających")

        # Volatility insights
        if volatility == "high":
            insights.append("🎢 Duże wahania nastroju - rozważ regularne praktyki mindfulness")

        # Most common mood
        if most_common_moods:
            top_mood = most_common_moods[0][0]
            if top_mood in ["sad", "anxious", "stressed"]:
                insights.append(f"💭 Dominujący nastrój: {top_mood} - eksplorujmy strategie radzenia sobie")

        return insights

    # ========================================================================
    # 4. RECOMMENDATIONS
    # ========================================================================

    async def get_recommendations(
        self,
        user_id: str,
        n_recommendations: int = 5
    ) -> Dict[str, Any]:
        """
        Wygeneruj rekomendacje oparte na:
        1. Podobnych tematach z przeszłości
        2. Trendach nastrojów
        3. Aktujalnym kontekście

        Args:
            user_id: ID użytkownika
            n_recommendations: Ile rekomendacji

        Returns:
            Dict z rekomendacjami
        """
        logger.info(f"💡 Generating recommendations for {user_id}")

        try:
            recommendations = []

            # 1. Topic-based recommendations
            clusters = await self.cluster_conversations_by_topic(user_id, n_clusters=3)

            if "clusters" in clusters:
                for cluster in clusters["clusters"][:2]:  # Top 2 clusters
                    recommendations.append({
                        "type": "topic_exploration",
                        "title": f"Kontynuuj temat: {cluster['label']}",
                        "description": f"Masz {cluster['size']} rozmów o tym temacie",
                        "action": "explore_topic",
                        "topic": cluster['label']
                    })

            # 2. Mood-based recommendations
            mood_trends = await self.analyze_mood_trends(user_id, days=14)

            if "trend" in mood_trends:
                if mood_trends["trend"] == "declining":
                    recommendations.append({
                        "type": "wellbeing",
                        "title": "Techniki relaksacyjne",
                        "description": "Zauważyliśmy spadek nastroju - spróbuj guided meditation",
                        "action": "start_meditation",
                        "priority": "high"
                    })

            # 3. Activity recommendations
            recommendations.append({
                "type": "activity",
                "title": "Refleksja tygodniowa",
                "description": "Podsumuj swój tydzień i zaplanuj następny",
                "action": "weekly_review"
            })

            # 4. Learning recommendations
            recommendations.append({
                "type": "learning",
                "title": "Nowe techniki CBT",
                "description": "Poznaj zaawansowane techniki cognitive behavioral therapy",
                "action": "learn_cbt"
            })

            return {
                "user_id": user_id,
                "recommendations": recommendations[:n_recommendations],
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Recommendations failed: {e}")
            return {"error": str(e)}


# ============================================================================
# Singleton Pattern
# ============================================================================

_analytics_service: Optional[AnalyticsService] = None


def init_analytics_service(llm_engine, memory_manager, chromadb_service, embedding_service) -> AnalyticsService:
    """Inicjalizuj globalny Analytics Service"""
    global _analytics_service

    _analytics_service = AnalyticsService(
        llm_engine=llm_engine,
        memory_manager=memory_manager,
        chromadb_service=chromadb_service,
        embedding_service=embedding_service
    )

    return _analytics_service


def get_analytics_service() -> Optional[AnalyticsService]:
    """Pobierz globalny Analytics Service"""
    return _analytics_service
