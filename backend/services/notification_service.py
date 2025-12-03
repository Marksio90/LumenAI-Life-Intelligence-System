"""
Notification Service - Proaktywne, inteligentne powiadomienia dla LumenAI

Ten serwis:
1. Wykrywa ważne wydarzenia (mood drops, patterns, anomalies)
2. Generuje smart notifications oparte na ML predictions
3. Wysyła powiadomienia real-time przez WebSocket
4. Planuje scheduled notifications (daily/weekly summaries)
5. Priorytetyzuje powiadomienia według ważności
"""

from typing import List, Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from loguru import logger
from enum import Enum
import asyncio
from dataclasses import dataclass, asdict
import json


class NotificationType(Enum):
    """Typy powiadomień"""
    MOOD_DROP = "mood_drop"
    MOOD_IMPROVEMENT = "mood_improvement"
    PATTERN_DETECTED = "pattern_detected"
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_SUMMARY = "weekly_summary"
    REMINDER = "reminder"
    RECOMMENDATION = "recommendation"
    ML_PREDICTION = "ml_prediction"
    ANOMALY = "anomaly"


class NotificationPriority(Enum):
    """Priorytety powiadomień"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    """Struktura powiadomienia"""
    notification_id: str
    user_id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    action: Optional[str] = None  # Sugerowana akcja
    action_url: Optional[str] = None  # Link do akcji
    metadata: Optional[Dict] = None
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    read: bool = False

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.expires_at is None:
            # Default: notifications expire after 7 days
            self.expires_at = self.created_at + timedelta(days=7)

    def to_dict(self) -> Dict:
        """Convert to dict for serialization"""
        data = asdict(self)
        data["type"] = self.type.value
        data["priority"] = self.priority.value
        data["created_at"] = self.created_at.isoformat()
        if self.expires_at:
            data["expires_at"] = self.expires_at.isoformat()
        return data


class NotificationService:
    """
    Serwis do zarządzania inteligentnymi powiadomieniami.

    Features:
    - Smart mood drop detection
    - Pattern recognition alerts
    - ML-based predictions
    - Scheduled summaries
    - Real-time push notifications
    """

    def __init__(
        self,
        memory_manager,
        training_service=None,
        analytics_service=None
    ):
        """
        Args:
            memory_manager: Memory Manager do dostępu do danych
            training_service: Optional ML Training Service
            analytics_service: Optional Analytics Service
        """
        self.memory = memory_manager
        self.ml_service = training_service
        self.analytics = analytics_service

        # Store for pending notifications
        self._notification_queue: List[Notification] = []

        # Callbacks for real-time delivery
        self._notification_callbacks: Dict[str, Callable] = {}

        # Background monitoring tasks
        self._monitoring_tasks: List[asyncio.Task] = []

        logger.info("🔔 Notification Service initialized")

    # ========================================================================
    # SMART DETECTION - Wykrywanie wydarzeń
    # ========================================================================

    async def detect_mood_drop(
        self,
        user_id: str,
        current_mood: float,
        threshold: float = 2.0
    ) -> Optional[Notification]:
        """
        Wykrywa spadek nastroju użytkownika.

        Porównuje obecny nastrój z ostatnimi dniami.
        Jeśli spadek > threshold, tworzy powiadomienie.

        Args:
            user_id: ID użytkownika
            current_mood: Aktualny nastrój (1-10)
            threshold: Minimalna różnica do trigger (default: 2.0)

        Returns:
            Notification jeśli wykryto spadek, None w przeciwnym razie
        """
        try:
            # Get recent mood history
            mood_history = await self.memory.get_mood_history(user_id, days=7)

            if len(mood_history) < 3:
                # Not enough data
                return None

            # Calculate average mood from last 7 days
            recent_moods = [m["mood_intensity"] for m in mood_history[:-1]]  # Exclude current
            avg_mood = sum(recent_moods) / len(recent_moods)

            # Check for significant drop
            mood_drop = avg_mood - current_mood

            if mood_drop >= threshold:
                logger.info(
                    f"Mood drop detected for user {user_id}: "
                    f"{avg_mood:.1f} -> {current_mood:.1f} (drop: {mood_drop:.1f})"
                )

                notification = Notification(
                    notification_id=f"mood_drop_{user_id}_{datetime.utcnow().timestamp()}",
                    user_id=user_id,
                    type=NotificationType.MOOD_DROP,
                    priority=NotificationPriority.HIGH if mood_drop >= 3.0 else NotificationPriority.MEDIUM,
                    title="Zauważyłem spadek nastroju",
                    message=f"Twój nastrój spadł o {mood_drop:.1f} punktów w porównaniu do ostatnich dni. "
                            f"Chcesz porozmawiać o tym, co się dzieje?",
                    action="start_conversation",
                    metadata={
                        "current_mood": current_mood,
                        "avg_mood": avg_mood,
                        "mood_drop": mood_drop
                    }
                )

                await self._queue_notification(notification)
                return notification

            return None

        except Exception as e:
            logger.error(f"Error detecting mood drop: {e}")
            return None

    async def detect_mood_improvement(
        self,
        user_id: str,
        current_mood: float,
        threshold: float = 2.0
    ) -> Optional[Notification]:
        """
        Wykrywa poprawę nastroju użytkownika.

        Gratuluje i wzmacnia pozytywne zmiany.
        """
        try:
            mood_history = await self.memory.get_mood_history(user_id, days=7)

            if len(mood_history) < 3:
                return None

            recent_moods = [m["mood_intensity"] for m in mood_history[:-1]]
            avg_mood = sum(recent_moods) / len(recent_moods)

            mood_improvement = current_mood - avg_mood

            if mood_improvement >= threshold:
                logger.info(
                    f"Mood improvement detected for user {user_id}: "
                    f"{avg_mood:.1f} -> {current_mood:.1f} (improvement: {mood_improvement:.1f})"
                )

                notification = Notification(
                    notification_id=f"mood_improvement_{user_id}_{datetime.utcnow().timestamp()}",
                    user_id=user_id,
                    type=NotificationType.MOOD_IMPROVEMENT,
                    priority=NotificationPriority.LOW,
                    title="🎉 Świetnie Ci idzie!",
                    message=f"Twój nastrój poprawił się o {mood_improvement:.1f} punktów! "
                            f"Widzę pozytywne zmiany. Co Ci pomogło?",
                    action="share_success",
                    metadata={
                        "current_mood": current_mood,
                        "avg_mood": avg_mood,
                        "mood_improvement": mood_improvement
                    }
                )

                await self._queue_notification(notification)
                return notification

            return None

        except Exception as e:
            logger.error(f"Error detecting mood improvement: {e}")
            return None

    async def detect_behavioral_pattern(
        self,
        user_id: str,
        pattern_type: str,
        pattern_data: Dict
    ) -> Notification:
        """
        Tworzy powiadomienie o wykrytym wzorcu zachowania.

        Args:
            user_id: ID użytkownika
            pattern_type: Typ wzorca (e.g., "stress_pattern", "sleep_pattern")
            pattern_data: Dane o wzorcu

        Returns:
            Notification
        """
        notification = Notification(
            notification_id=f"pattern_{user_id}_{datetime.utcnow().timestamp()}",
            user_id=user_id,
            type=NotificationType.PATTERN_DETECTED,
            priority=NotificationPriority.MEDIUM,
            title=f"Wykryłem wzorzec: {pattern_type}",
            message=self._generate_pattern_message(pattern_type, pattern_data),
            action="view_pattern_details",
            metadata={
                "pattern_type": pattern_type,
                "pattern_data": pattern_data
            }
        )

        await self._queue_notification(notification)
        return notification

    def _generate_pattern_message(self, pattern_type: str, data: Dict) -> str:
        """Generuje wiadomość o wzorcu"""
        messages = {
            "stress_pattern": "Zauważyłem, że Twój stres rośnie w określonych porach. Może warto to przeanalizować?",
            "sleep_pattern": "Widzę wzorzec w Twoim śnie. Twoje samopoczucie jest lepsze gdy śpisz regularnie.",
            "activity_pattern": "Rozmowy w określonych godzinach sprawiają, że czujesz się lepiej.",
            "conversation_pattern": "Zauważyłem, że najczęściej rozmawiamy o podobnych tematach."
        }
        return messages.get(pattern_type, f"Wykryłem ciekawy wzorzec w Twoich danych.")

    # ========================================================================
    # ML-BASED NOTIFICATIONS
    # ========================================================================

    async def check_ml_predictions(self, user_id: str, current_message: str) -> Optional[Notification]:
        """
        Sprawdza predykcje ML i tworzy powiadomienie jeśli potrzebne.

        Args:
            user_id: ID użytkownika
            current_message: Aktualna wiadomość

        Returns:
            Notification jeśli ML wykrył coś ważnego
        """
        if not self.ml_service:
            return None

        try:
            # Get ML predictions
            mood_pred = await self.ml_service.predict_mood(user_id, current_message)
            behavior_pred = await self.ml_service.predict_behavior(user_id, current_message)

            if not mood_pred or not behavior_pred:
                return None

            # Check for concerning predictions
            predicted_mood = mood_pred["predicted_mood"]
            predicted_behavior = behavior_pred["predicted_class"]

            # Low mood prediction
            if predicted_mood < 4.0:
                notification = Notification(
                    notification_id=f"ml_pred_{user_id}_{datetime.utcnow().timestamp()}",
                    user_id=user_id,
                    type=NotificationType.ML_PREDICTION,
                    priority=NotificationPriority.HIGH,
                    title="Wyczuwam, że możesz potrzebować wsparcia",
                    message=f"Na podstawie naszej rozmowy przewiduję, że możesz czuć się gorzej. "
                            f"Chcesz o tym porozmawiać?",
                    action="start_support_conversation",
                    metadata={
                        "predicted_mood": predicted_mood,
                        "predicted_behavior": predicted_behavior
                    }
                )

                await self._queue_notification(notification)
                return notification

            # Negative behavior pattern
            if predicted_behavior == "negative" and behavior_pred["probabilities"]["negative"] > 0.7:
                notification = Notification(
                    notification_id=f"ml_behavior_{user_id}_{datetime.utcnow().timestamp()}",
                    user_id=user_id,
                    type=NotificationType.ML_PREDICTION,
                    priority=NotificationPriority.MEDIUM,
                    title="Zauważyłem zmianę w Twoim tonie",
                    message="Wygląda na to, że coś Cię niepokoi. Mogę pomóc?",
                    action="start_support_conversation",
                    metadata={
                        "predicted_behavior": predicted_behavior,
                        "confidence": behavior_pred["probabilities"]["negative"]
                    }
                )

                await self._queue_notification(notification)
                return notification

            return None

        except Exception as e:
            logger.error(f"Error checking ML predictions: {e}")
            return None

    # ========================================================================
    # SCHEDULED NOTIFICATIONS - Podsumowania
    # ========================================================================

    async def generate_daily_summary(self, user_id: str) -> Notification:
        """
        Generuje codzienne podsumowanie dla użytkownika.

        Podsumowanie zawiera:
        - Nastrój z dzisiaj
        - Główne tematy rozmów
        - Sugestie na jutro
        """
        try:
            # Get today's data
            today = datetime.utcnow().date()
            mood_history = await self.memory.get_mood_history(user_id, days=1)

            summary_parts = []

            # Mood summary
            if mood_history:
                avg_mood = sum(m["mood_intensity"] for m in mood_history) / len(mood_history)
                summary_parts.append(f"📊 Średni nastrój dzisiaj: {avg_mood:.1f}/10")

            # Get analytics if available
            if self.analytics:
                try:
                    trends = await self.analytics.analyze_mood_trends(user_id, days=1)
                    summary_parts.append(f"📈 Trend: {trends.get('trend', 'stabilny')}")
                except:
                    pass

            summary_message = "\n".join(summary_parts) if summary_parts else "Brak danych z dzisiaj."

            notification = Notification(
                notification_id=f"daily_summary_{user_id}_{datetime.utcnow().timestamp()}",
                user_id=user_id,
                type=NotificationType.DAILY_SUMMARY,
                priority=NotificationPriority.LOW,
                title="📅 Twoje podsumowanie dnia",
                message=summary_message,
                action="view_full_summary",
                metadata={"date": str(today)}
            )

            await self._queue_notification(notification)
            return notification

        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            return None

    async def generate_weekly_summary(self, user_id: str) -> Notification:
        """
        Generuje tygodniowe podsumowanie dla użytkownika.

        Głębsza analiza:
        - Trendy nastrojów
        - Wzorce zachowań
        - Rekomendacje na przyszły tydzień
        """
        try:
            # Get week's data
            mood_history = await self.memory.get_mood_history(user_id, days=7)

            summary_parts = []

            if mood_history:
                moods = [m["mood_intensity"] for m in mood_history]
                avg_mood = sum(moods) / len(moods)
                max_mood = max(moods)
                min_mood = min(moods)

                summary_parts.append(f"📊 Średni nastrój tygodnia: {avg_mood:.1f}/10")
                summary_parts.append(f"📈 Najlepszy dzień: {max_mood:.1f}/10")
                summary_parts.append(f"📉 Najtrudniejszy dzień: {min_mood:.1f}/10")

            # Get analytics
            if self.analytics:
                try:
                    trends = await self.analytics.analyze_mood_trends(user_id, days=7)
                    summary_parts.append(f"\n💡 Trend: {trends.get('trend', 'stabilny')}")

                    recommendations = await self.analytics.get_recommendations(user_id, n_recommendations=3)
                    if recommendations and recommendations.get("recommendations"):
                        summary_parts.append("\n✨ Rekomendacje na przyszły tydzień:")
                        for rec in recommendations["recommendations"][:3]:
                            summary_parts.append(f"  • {rec['title']}")
                except:
                    pass

            summary_message = "\n".join(summary_parts) if summary_parts else "Brak wystarczających danych."

            notification = Notification(
                notification_id=f"weekly_summary_{user_id}_{datetime.utcnow().timestamp()}",
                user_id=user_id,
                type=NotificationType.WEEKLY_SUMMARY,
                priority=NotificationPriority.MEDIUM,
                title="📅 Twoje podsumowanie tygodnia",
                message=summary_message,
                action="view_full_weekly_summary",
                metadata={"week_start": str(datetime.utcnow().date() - timedelta(days=7))}
            )

            await self._queue_notification(notification)
            return notification

        except Exception as e:
            logger.error(f"Error generating weekly summary: {e}")
            return None

    # ========================================================================
    # NOTIFICATION QUEUE MANAGEMENT
    # ========================================================================

    async def _queue_notification(self, notification: Notification):
        """Dodaje powiadomienie do kolejki i wysyła real-time"""
        self._notification_queue.append(notification)

        # Immediately deliver if callback registered
        if notification.user_id in self._notification_callbacks:
            callback = self._notification_callbacks[notification.user_id]
            try:
                await callback(notification)
                logger.info(f"Notification delivered real-time to {notification.user_id}")
            except Exception as e:
                logger.error(f"Error delivering notification: {e}")

    def register_callback(self, user_id: str, callback: Callable):
        """
        Rejestruje callback do real-time delivery powiadomień.

        Args:
            user_id: ID użytkownika
            callback: Async function do wywołania z Notification
        """
        self._notification_callbacks[user_id] = callback
        logger.debug(f"Registered notification callback for user {user_id}")

    def unregister_callback(self, user_id: str):
        """Wyrejestrowuje callback"""
        if user_id in self._notification_callbacks:
            del self._notification_callbacks[user_id]
            logger.debug(f"Unregistered notification callback for user {user_id}")

    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict]:
        """
        Pobiera powiadomienia użytkownika.

        Args:
            user_id: ID użytkownika
            unread_only: Tylko nieprzeczytane
            limit: Max liczba powiadomień

        Returns:
            Lista powiadomień jako Dict
        """
        notifications = [
            n for n in self._notification_queue
            if n.user_id == user_id and (not unread_only or not n.read)
        ]

        # Sort by priority and time
        priority_order = {
            NotificationPriority.URGENT: 0,
            NotificationPriority.HIGH: 1,
            NotificationPriority.MEDIUM: 2,
            NotificationPriority.LOW: 3
        }

        notifications.sort(
            key=lambda n: (priority_order[n.priority], n.created_at),
            reverse=True
        )

        return [n.to_dict() for n in notifications[:limit]]

    async def mark_as_read(self, notification_id: str):
        """Oznacza powiadomienie jako przeczytane"""
        for notification in self._notification_queue:
            if notification.notification_id == notification_id:
                notification.read = True
                logger.debug(f"Notification {notification_id} marked as read")
                return True
        return False


# ============================================================================
# Singleton Pattern
# ============================================================================

_notification_service: Optional[NotificationService] = None


def init_notification_service(
    memory_manager,
    training_service=None,
    analytics_service=None
) -> NotificationService:
    """Inicjalizuj globalny Notification Service"""
    global _notification_service

    _notification_service = NotificationService(
        memory_manager=memory_manager,
        training_service=training_service,
        analytics_service=analytics_service
    )

    return _notification_service


def get_notification_service() -> Optional[NotificationService]:
    """Pobierz globalny Notification Service"""
    return _notification_service
