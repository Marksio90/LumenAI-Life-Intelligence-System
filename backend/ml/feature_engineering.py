"""
Feature Engineering - Ekstrakcja cech z danych użytkownika dla ML

Ten moduł przekształca surowe dane użytkownika w features gotowe do treningu ML:
- Temporal features (czas, dzień tygodnia, pora dnia)
- Conversation features (długość, sentiment, tematy)
- Mood features (historia nastrojów, trendy)
- Behavior features (wzorce aktywności, regularność)
- Context features (kontekst rozmów, embeddingi)
"""

from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from loguru import logger
import numpy as np
from collections import Counter, defaultdict
import statistics


class FeatureEngineer:
    """
    Ekstrakcja i inżynieria cech z danych użytkownika.

    Generuje kompleksowy feature vector dla każdej próbki danych,
    gotowy do użycia w modelach ML.
    """

    def __init__(self, memory_manager, embedding_service=None):
        """
        Args:
            memory_manager: Memory Manager do dostępu do danych
            embedding_service: Optional - dla semantic features
        """
        self.memory = memory_manager
        self.embeddings = embedding_service
        logger.info("🔧 Feature Engineer initialized")

    # ========================================================================
    # TEMPORAL FEATURES - Cechy czasowe
    # ========================================================================

    def extract_temporal_features(self, timestamp: datetime) -> Dict[str, float]:
        """
        Ekstrakcja cech czasowych z timestamp.

        Cechy:
        - hour_of_day (0-23)
        - day_of_week (0-6, gdzie 0=Poniedziałek)
        - is_weekend (0/1)
        - is_morning/afternoon/evening/night (0/1)
        - day_of_month (1-31)
        - week_of_year (1-52)

        Args:
            timestamp: Datetime object

        Returns:
            Dict z cechami czasowymi
        """
        hour = timestamp.hour
        day_of_week = timestamp.weekday()

        features = {
            "hour_of_day": hour,
            "day_of_week": day_of_week,
            "is_weekend": 1.0 if day_of_week >= 5 else 0.0,
            "is_morning": 1.0 if 6 <= hour < 12 else 0.0,
            "is_afternoon": 1.0 if 12 <= hour < 18 else 0.0,
            "is_evening": 1.0 if 18 <= hour < 22 else 0.0,
            "is_night": 1.0 if hour >= 22 or hour < 6 else 0.0,
            "day_of_month": float(timestamp.day),
            "week_of_year": float(timestamp.isocalendar()[1])
        }

        return features

    # ========================================================================
    # CONVERSATION FEATURES - Cechy rozmów
    # ========================================================================

    async def extract_conversation_features(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Ekstrakcja cech z rozmowy.

        Cechy:
        - message_length (długość wiadomości)
        - word_count (liczba słów)
        - question_marks (liczba pytań)
        - exclamation_marks (emocjonalność)
        - sentiment_score (szacowany sentiment)
        - conversation_turn (numer tury w konwersacji)
        - avg_response_length (średnia długość odpowiedzi użytkownika)

        Args:
            user_id: ID użytkownika
            message: Treść wiadomości
            conversation_id: Optional - ID konwersacji

        Returns:
            Dict z cechami konwersacji
        """
        features = {
            "message_length": float(len(message)),
            "word_count": float(len(message.split())),
            "question_marks": float(message.count("?")),
            "exclamation_marks": float(message.count("!")),
            "has_negative_words": self._count_negative_words(message),
            "has_positive_words": self._count_positive_words(message),
        }

        # Sentiment approximation (simple heuristic)
        sentiment = 0.0
        if features["has_positive_words"] > features["has_negative_words"]:
            sentiment = 1.0
        elif features["has_negative_words"] > features["has_positive_words"]:
            sentiment = -1.0
        features["sentiment_approx"] = sentiment

        # Conversation context features
        if conversation_id:
            try:
                db = self.memory._get_mongodb()
                if db:
                    messages = await db.get_conversation_messages(conversation_id, limit=100)
                    features["conversation_turn"] = float(len(messages))

                    # Average message length in this conversation
                    user_messages = [m for m in messages if m.role == "user"]
                    if user_messages:
                        avg_len = sum(len(m.content) for m in user_messages) / len(user_messages)
                        features["avg_message_length"] = avg_len
                    else:
                        features["avg_message_length"] = 0.0
                else:
                    features["conversation_turn"] = 0.0
                    features["avg_message_length"] = 0.0
            except Exception as e:
                logger.debug(f"Could not extract conversation features: {e}")
                features["conversation_turn"] = 0.0
                features["avg_message_length"] = 0.0
        else:
            features["conversation_turn"] = 0.0
            features["avg_message_length"] = 0.0

        return features

    def _count_negative_words(self, text: str) -> float:
        """Policzy słowa negatywne (prosty heurystyk)"""
        negative_words = [
            "smutny", "smutna", "zły", "zła", "źle", "kiepsko", "problem",
            "trudność", "stres", "lęk", "depresja", "ból", "choroba",
            "nie", "nigdy", "nic", "nikt", "gorszy", "gorsza"
        ]
        text_lower = text.lower()
        return float(sum(1 for word in negative_words if word in text_lower))

    def _count_positive_words(self, text: str) -> float:
        """Policzy słowa pozytywne (prosty heurystyk)"""
        positive_words = [
            "dobry", "dobra", "dobrze", "świetny", "świetnie", "super",
            "wspaniale", "radość", "szczęście", "miłość", "sukces",
            "tak", "można", "lepiej", "lepsza", "lepszy"
        ]
        text_lower = text.lower()
        return float(sum(1 for word in positive_words if word in text_lower))

    # ========================================================================
    # MOOD FEATURES - Cechy nastroju
    # ========================================================================

    async def extract_mood_features(
        self,
        user_id: str,
        lookback_days: int = 7
    ) -> Dict[str, float]:
        """
        Ekstrakcja cech nastroju z historii.

        Cechy:
        - recent_mood_avg (średni nastrój z ostatnich N dni)
        - recent_mood_std (odchylenie standardowe)
        - recent_mood_trend (trend: rosnący/spadający)
        - mood_volatility (zmienność)
        - days_since_last_positive (dni od ostatniego pozytywnego nastroju)
        - days_since_last_negative (dni od ostatniego negatywnego nastroju)

        Args:
            user_id: ID użytkownika
            lookback_days: Ile dni wstecz analizować

        Returns:
            Dict z cechami nastroju
        """
        try:
            mood_history = await self.memory.get_mood_history(user_id, days=lookback_days)

            if not mood_history:
                return self._default_mood_features()

            # Extract mood intensities and timestamps
            moods = []
            timestamps = []
            for entry in mood_history:
                moods.append(entry["mood_intensity"])
                timestamps.append(datetime.fromisoformat(entry["timestamp"]))

            features = {}

            # Basic statistics
            features["recent_mood_avg"] = statistics.mean(moods)
            features["recent_mood_std"] = statistics.stdev(moods) if len(moods) > 1 else 0.0
            features["recent_mood_min"] = min(moods)
            features["recent_mood_max"] = max(moods)

            # Trend (simple linear regression slope)
            if len(moods) >= 2:
                x = np.arange(len(moods))
                slope = np.polyfit(x, moods, 1)[0]
                features["recent_mood_trend"] = float(slope)
            else:
                features["recent_mood_trend"] = 0.0

            # Volatility (coefficient of variation)
            if features["recent_mood_avg"] != 0:
                features["mood_volatility"] = features["recent_mood_std"] / abs(features["recent_mood_avg"])
            else:
                features["mood_volatility"] = 0.0

            # Days since last positive/negative mood
            now = datetime.utcnow()
            last_positive = None
            last_negative = None

            for i, mood in enumerate(moods):
                if mood > 6 and not last_positive:
                    last_positive = timestamps[i]
                if mood < 4 and not last_negative:
                    last_negative = timestamps[i]

            features["days_since_last_positive"] = (now - last_positive).days if last_positive else 999.0
            features["days_since_last_negative"] = (now - last_negative).days if last_negative else 999.0

            # Mood distribution
            mood_counts = Counter([self._categorize_mood(m) for m in moods])
            features["pct_positive_moods"] = mood_counts.get("positive", 0) / len(moods)
            features["pct_neutral_moods"] = mood_counts.get("neutral", 0) / len(moods)
            features["pct_negative_moods"] = mood_counts.get("negative", 0) / len(moods)

            return features

        except Exception as e:
            logger.debug(f"Could not extract mood features: {e}")
            return self._default_mood_features()

    def _categorize_mood(self, intensity: float) -> str:
        """Kategoryzuje nastrój na positive/neutral/negative"""
        if intensity >= 7:
            return "positive"
        elif intensity <= 4:
            return "negative"
        else:
            return "neutral"

    def _default_mood_features(self) -> Dict[str, float]:
        """Domyślne features gdy brak danych"""
        return {
            "recent_mood_avg": 5.0,
            "recent_mood_std": 0.0,
            "recent_mood_min": 5.0,
            "recent_mood_max": 5.0,
            "recent_mood_trend": 0.0,
            "mood_volatility": 0.0,
            "days_since_last_positive": 999.0,
            "days_since_last_negative": 999.0,
            "pct_positive_moods": 0.0,
            "pct_neutral_moods": 1.0,
            "pct_negative_moods": 0.0
        }

    # ========================================================================
    # BEHAVIOR FEATURES - Cechy zachowania
    # ========================================================================

    async def extract_behavior_features(
        self,
        user_id: str,
        lookback_days: int = 30
    ) -> Dict[str, float]:
        """
        Ekstrakcja cech behawioralnych użytkownika.

        Cechy:
        - total_conversations (liczba konwersacji)
        - avg_conversations_per_day (średnia dzienna)
        - total_messages (liczba wiadomości)
        - avg_message_length (średnia długość)
        - most_active_hour (najaktywniejsza godzina)
        - most_active_day (najaktywniejszy dzień tygodnia)
        - conversation_regularity (regularność rozmów)
        - agents_diversity (ile różnych agentów używa)

        Args:
            user_id: ID użytkownika
            lookback_days: Ile dni wstecz analizować

        Returns:
            Dict z cechami behawioralnymi
        """
        try:
            db = self.memory._get_mongodb()
            if not db:
                return self._default_behavior_features()

            # Get conversations from last N days
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            conversations = await db.get_user_conversations(user_id, limit=1000)

            # Filter by date
            recent_convs = [
                c for c in conversations
                if c.started_at >= cutoff_date
            ]

            if not recent_convs:
                return self._default_behavior_features()

            features = {}

            # Conversation metrics
            features["total_conversations"] = float(len(recent_convs))
            features["avg_conversations_per_day"] = len(recent_convs) / lookback_days

            # Message metrics
            total_messages = sum(c.message_count for c in recent_convs)
            features["total_messages"] = float(total_messages)
            features["avg_messages_per_conversation"] = total_messages / len(recent_convs)

            # Temporal patterns
            hours = [c.started_at.hour for c in recent_convs]
            days = [c.started_at.weekday() for c in recent_convs]

            hour_counts = Counter(hours)
            day_counts = Counter(days)

            features["most_active_hour"] = float(hour_counts.most_common(1)[0][0])
            features["most_active_day"] = float(day_counts.most_common(1)[0][0])

            # Conversation regularity (coefficient of variation of inter-conversation times)
            if len(recent_convs) >= 2:
                sorted_convs = sorted(recent_convs, key=lambda c: c.started_at)
                inter_times = [
                    (sorted_convs[i+1].started_at - sorted_convs[i].started_at).total_seconds() / 3600
                    for i in range(len(sorted_convs) - 1)
                ]
                if inter_times:
                    avg_inter = statistics.mean(inter_times)
                    std_inter = statistics.stdev(inter_times) if len(inter_times) > 1 else 0.0
                    features["conversation_regularity"] = std_inter / avg_inter if avg_inter > 0 else 0.0
                    features["avg_hours_between_conversations"] = avg_inter
                else:
                    features["conversation_regularity"] = 0.0
                    features["avg_hours_between_conversations"] = 0.0
            else:
                features["conversation_regularity"] = 0.0
                features["avg_hours_between_conversations"] = 0.0

            # Agent diversity
            all_agents = []
            for conv in recent_convs:
                all_agents.extend(conv.agents_used)
            unique_agents = len(set(all_agents))
            features["agents_diversity"] = float(unique_agents)

            # Most used agent
            if all_agents:
                agent_counts = Counter(all_agents)
                features["most_used_agent_id"] = float(hash(agent_counts.most_common(1)[0][0]) % 100)
            else:
                features["most_used_agent_id"] = 0.0

            return features

        except Exception as e:
            logger.debug(f"Could not extract behavior features: {e}")
            return self._default_behavior_features()

    def _default_behavior_features(self) -> Dict[str, float]:
        """Domyślne behavior features gdy brak danych"""
        return {
            "total_conversations": 0.0,
            "avg_conversations_per_day": 0.0,
            "total_messages": 0.0,
            "avg_messages_per_conversation": 0.0,
            "most_active_hour": 12.0,
            "most_active_day": 0.0,
            "conversation_regularity": 0.0,
            "avg_hours_between_conversations": 0.0,
            "agents_diversity": 0.0,
            "most_used_agent_id": 0.0
        }

    # ========================================================================
    # SEMANTIC FEATURES - Cechy semantyczne (embeddings)
    # ========================================================================

    async def extract_semantic_features(
        self,
        message: str
    ) -> Dict[str, np.ndarray]:
        """
        Ekstrakcja cech semantycznych z embeddings.

        Zwraca embedding vector (1536 dimensions) dla wiadomości.

        Args:
            message: Treść wiadomości

        Returns:
            Dict z embedding vector
        """
        try:
            if not self.embeddings:
                return {"embedding": np.zeros(1536)}

            embedding = await self.embeddings.generate(message)
            return {"embedding": np.array(embedding)}

        except Exception as e:
            logger.debug(f"Could not extract semantic features: {e}")
            return {"embedding": np.zeros(1536)}

    # ========================================================================
    # MAIN FEATURE EXTRACTION
    # ========================================================================

    async def extract_all_features(
        self,
        user_id: str,
        message: str,
        timestamp: datetime,
        conversation_id: Optional[str] = None,
        include_embeddings: bool = False
    ) -> Tuple[Dict[str, float], Optional[np.ndarray]]:
        """
        Ekstrakcja WSZYSTKICH cech dla danej próbki.

        Kombinuje wszystkie typy features w jeden feature vector.

        Args:
            user_id: ID użytkownika
            message: Treść wiadomości
            timestamp: Timestamp wiadomości
            conversation_id: Optional - ID konwersacji
            include_embeddings: Czy dołączyć embeddingi (duży wymiar)

        Returns:
            Tuple (features_dict, embedding_array)
            - features_dict: Wszystkie skalarne features
            - embedding_array: Opcjonalny embedding vector
        """
        logger.debug(f"Extracting features for user {user_id}")

        # Extract all feature types
        temporal = self.extract_temporal_features(timestamp)
        conversation = await self.extract_conversation_features(user_id, message, conversation_id)
        mood = await self.extract_mood_features(user_id, lookback_days=7)
        behavior = await self.extract_behavior_features(user_id, lookback_days=30)

        # Combine all scalar features
        all_features = {
            **temporal,
            **conversation,
            **mood,
            **behavior
        }

        # Optional: Add embeddings
        embedding = None
        if include_embeddings:
            semantic = await self.extract_semantic_features(message)
            embedding = semantic["embedding"]

        logger.debug(f"Extracted {len(all_features)} scalar features + embedding={embedding is not None}")

        return all_features, embedding

    def features_to_vector(self, features: Dict[str, float]) -> np.ndarray:
        """
        Konwersja dict features na numpy array.

        Sortuje features alfabetycznie dla konsystencji.

        Args:
            features: Dict ze features

        Returns:
            Numpy array z wartościami features
        """
        # Sort keys alphabetically for consistency
        sorted_keys = sorted(features.keys())
        vector = np.array([features[k] for k in sorted_keys])
        return vector

    def get_feature_names(self, features: Dict[str, float]) -> List[str]:
        """
        Zwraca nazwy features w kolejności użytej w features_to_vector.

        Args:
            features: Dict ze features

        Returns:
            Lista nazw features
        """
        return sorted(features.keys())
