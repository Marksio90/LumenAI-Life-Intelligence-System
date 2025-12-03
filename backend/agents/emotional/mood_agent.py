"""
Mood Agent - Emotional support, mental health, and therapy
Based on CBT/DBT principles
"""

from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime

from backend.agents.base import BaseAgent


class MoodAgent(BaseAgent):
    """
    Specialized agent for emotional support and mental health
    - Mood tracking
    - Emotional support
    - CBT/DBT techniques
    - Stress management
    """

    def __init__(self, memory_manager=None):
        super().__init__(
            name="Mood",
            description="Wsparcie emocjonalne, zdrowie psychiczne i zarządzanie nastrojem",
            memory_manager=memory_manager
        )

    async def process(
        self,
        user_id: str,
        message: str,
        context: Dict[str, Any],
        metadata: Optional[Dict] = None
    ) -> str:
        """Process emotional support requests"""

        logger.info(f"Mood Agent processing for {user_id}")

        # Analyze emotional state
        emotion_analysis = await self._analyze_emotion(message)

        # Determine intervention type
        if emotion_analysis["intensity"] > 0.7:
            # High intensity emotion - provide immediate support
            return await self._provide_emotional_support(message, emotion_analysis, context)
        else:
            # General mood check
            return await self._general_mood_conversation(message, emotion_analysis, context)

    async def _analyze_emotion(self, message: str) -> Dict[str, Any]:
        """Analyze emotional content of message"""

        system_prompt = """
Przeanalizuj emocjonalny ton wiadomości użytkownika.

Zwróć JSON:
{
    "primary_emotion": "smutek/radość/złość/niepokój/neutralny",
    "intensity": 0.8,
    "indicators": ["słowa wskazujące na emocję"],
    "needs_support": true/false
}
"""

        try:
            response = await self._call_llm(
                prompt=f"Wiadomość: {message}",
                system_prompt=system_prompt
            )

            import json
            return json.loads(response)

        except Exception as e:
            logger.error(f"Emotion analysis error: {e}")
            return {
                "primary_emotion": "neutralny",
                "intensity": 0.5,
                "needs_support": False
            }

    async def _provide_emotional_support(
        self,
        message: str,
        emotion_analysis: Dict,
        context: Dict
    ) -> str:
        """Provide emotional support using CBT/DBT techniques"""

        emotion = emotion_analysis.get("primary_emotion", "unknown")

        system_prompt = f"""
Jesteś empatycznym wsparciem emocjonalnym wykorzystującym techniki CBT i DBT.

Użytkownik wyraża: {emotion}

Twoja odpowiedź powinna:
1. Walidować emocje (akceptacja bez osądzania)
2. Pokazać zrozumienie
3. Zaproponować prostą technikę radzenia sobie (np. oddychanie, reframing, grounding)
4. Dać nadzieję, ale być realistycznym

Bądź ciepły, autentyczny, konkretny. Unikaj banałów typu "będzie dobrze".
Mów po polsku naturalnie.
"""

        response = await self._call_llm(
            prompt=f"Użytkownik: {message}",
            system_prompt=system_prompt
        )

        # Add mood tracking suggestion
        tracking_prompt = "\n\n💙 *Czy chcesz, żebym śledzić Twój nastrój? Pomogę Ci zauważyć wzorce.*"

        return response + tracking_prompt

    async def _general_mood_conversation(
        self,
        message: str,
        emotion_analysis: Dict,
        context: Dict
    ) -> str:
        """General conversation about emotions and mood"""

        system_prompt = """
Jesteś przyjaznym towarzyszem rozmowy o emocjach i samopoczuciu.

Słuchaj aktywnie, pytaj o szczegóły, pomagaj użytkownikowi zrozumieć swoje emocje.
Używaj refleksyjnego słuchania.

Bądź naturalny, ciepły, konkretny.
"""

        response = await self._call_llm(message, system_prompt)
        return response

    async def track_mood(self, user_id: str, mood_data: Dict):
        """Track user's mood over time - NOW SAVES TO MONGODB! 💾"""

        # Save mood to MongoDB via memory_manager
        if self.memory_manager:
            entry_id = await self.memory_manager.save_mood_entry(
                user_id=user_id,
                mood_data={
                    "primary": mood_data.get("mood", "neutral"),
                    "intensity": mood_data.get("intensity", 5),
                    "description": mood_data.get("notes"),
                    "triggers": mood_data.get("triggers", [])
                }
            )
            logger.info(f"😊 Tracked mood for {user_id}: {mood_data.get('mood')} (saved to DB: {entry_id})")
            return {"entry_id": entry_id, **mood_data}
        else:
            logger.warning(f"Memory manager not available, mood not saved for {user_id}")
            return mood_data

    async def get_mood_insights(self, user_id: str, days: int = 7) -> str:
        """Get mood insights and patterns - NOW WITH REAL DATA FROM MONGODB! 📊"""

        if not self.memory_manager:
            return "Statystyki nastrojów niedostępne (brak połączenia z bazą danych)."

        # Get mood statistics from MongoDB
        stats = await self.memory_manager.get_mood_statistics(user_id, days=days)

        if not stats or stats.get("total_entries") == 0:
            return f"📊 **Brak danych o nastrojach z ostatnich {days} dni.**\n\nZacznij śledzić swoje emocje, a ja pomogę Ci zauważyć wzorce! 💙"

        # Generate insights based on real data
        most_common = stats.get("most_common_mood", "neutral")
        avg_intensity = stats.get("average_intensity", 5)
        total = stats.get("total_entries", 0)
        distribution = stats.get("mood_distribution", {})

        mood_emojis = {
            "happy": "😊",
            "sad": "😢",
            "anxious": "😰",
            "angry": "😠",
            "neutral": "😐",
            "excited": "🎉",
            "tired": "😴",
            "stressed": "😓"
        }

        insights = f"""
📊 **Twoje emocje w ostatnich {days} dni:**

🌈 **Dominujący nastrój:** {mood_emojis.get(most_common, '💙')} {most_common.capitalize()}
📊 **Średnia intensywność:** {avg_intensity}/10
📝 **Liczba wpisów:** {total}

**Rozkład emocji:**
"""

        for mood, count in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
            emoji = mood_emojis.get(mood, '•')
            insights += f"\n{emoji} {mood.capitalize()}: {count}x"

        insights += "\n\n💡 **Kontynuuj śledzenie swoich emocji - im więcej danych, tym lepsze wzorce zauważę!**"

        return insights

    async def can_handle(self, message: str, context: Dict) -> float:
        """Check if this agent should handle the message"""

        emotional_keywords = [
            "czuję", "emocje", "nastrój", "smutek", "radość", "stres",
            "niepokój", "lęk", "depresja", "szczęście", "płaczę", "boi"
        ]

        message_lower = message.lower()
        matches = sum(1 for keyword in emotional_keywords if keyword in message_lower)

        return min(matches * 0.4, 1.0)
