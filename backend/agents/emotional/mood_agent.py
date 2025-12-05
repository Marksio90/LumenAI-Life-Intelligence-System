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

    def __init__(self, memory_manager=None, llm_engine=None):
        super().__init__(
            name="Mood",
            description="Wsparcie emocjonalne, zdrowie psychiczne i zarządzanie nastrojem",
            memory_manager=memory_manager,
            llm_engine=llm_engine
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
        intensity = emotion_analysis.get("intensity", 0.5)

        # Detect cognitive distortions
        distortions = await self.detect_cognitive_distortions(message)

        system_prompt = f"""
Jesteś empatycznym wsparciem emocjonalnym wykorzystującym techniki CBT i DBT.

Użytkownik wyraża: {emotion} (intensywność: {intensity})

Twoja odpowiedź powinna:
1. Walidować emocje (akceptacja bez osądzania)
2. Pokazać zrozumienie
3. Delikatnie zwrócić uwagę na zniekształcenia poznawcze (jeśli są)
4. Dać nadzieję, ale być realistycznym

Bądź ciepły, autentyczny, konkretny. Unikaj banałów typu "będzie dobrze".
Mów po polsku naturalnie.
"""

        response = await self._call_llm(
            prompt=f"Użytkownik: {message}",
            system_prompt=system_prompt
        )

        # Add CBT technique suggestion
        technique = await self.suggest_cbt_technique(emotion, intensity)
        response += f"\n\n{technique}"

        # Add cognitive distortion reframe if found
        if distortions.get("distortions_found"):
            response += f"\n\n💭 **Zauważyłem wzorzec myślenia:**"
            for i, (distortion, reframe) in enumerate(zip(
                distortions.get("distortions_found", []),
                distortions.get("reframes", [])
            )):
                response += f"\n• {distortion}: {reframe}"

        # Add mood tracking suggestion
        tracking_prompt = "\n\n💙 *Chcesz żebym śledził Twój nastrój? Pomogę Ci zauważyć wzorce.*"

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

    async def suggest_cbt_technique(self, emotion: str, intensity: float) -> str:
        """Suggest appropriate CBT/DBT technique based on emotion"""

        techniques = {
            "anxious": {
                "high": "🧘 **5-4-3-2-1 Grounding**: Wymień 5 rzeczy które widzisz, 4 które słyszysz, 3 które czujesz, 2 które czujesz zapachem, 1 którą czujesz smakiem.",
                "medium": "💨 **Box Breathing**: Wdech 4s → Wstrzymaj 4s → Wydech 4s → Wstrzymaj 4s. Powtórz 4 razy.",
                "low": "📝 **Thought Check**: Czy ten niepokój jest oparty na faktach czy domysłach?"
            },
            "sad": {
                "high": "🌟 **Behavioral Activation**: Zrób małą rzecz która kiedyś sprawiała Ci radość. Nawet 5 minut.",
                "medium": "💭 **Reframing**: Zamień 'To nigdy się nie zmieni' na 'To jest trudne teraz, ale mogę wpłynąć na małe rzeczy'.",
                "low": "✍️ **Gratitude List**: Wymień 3 małe rzeczy za które jesteś wdzięczny dzisiaj."
            },
            "angry": {
                "high": "🚶 **Physical Release**: Idź na spacer, zrób 10 przysiądów lub pokrzycz do poduszki.",
                "medium": "⏸️ **STOP Technique**: Stop → Take a breath → Observe → Proceed mindfully",
                "low": "🎯 **Assertive Communication**: Opisz uczucie bez oskarżania: 'Czuję się... gdy... ponieważ...'"
            },
            "stressed": {
                "high": "💆 **Progressive Muscle Relaxation**: Naprężaj i rozluźniaj każdą grupę mięśni od stóp do głowy.",
                "medium": "📋 **Brain Dump**: Wypisz wszystko co Cię stresuje. Potem kategoryzuj: co mogę kontrolować?",
                "low": "🎵 **Sensory Break**: 5 minut muzyki/natury bez telefonu."
            },
            "neutral": {
                "high": "🧘 **Mindful Check-in**: Jak się naprawdę czujesz? Gdzie czujesz to w ciele?",
                "medium": "💪 **Value Action**: Zrób dzisiaj jedną rzecz zgodną z Twoimi wartościami.",
                "low": "🌱 **Micro-Habit**: Jaką małą rzecz możesz zrobić dla siebie dzisiaj?"
            }
        }

        emotion_key = emotion if emotion in techniques else "neutral"
        intensity_key = "high" if intensity > 0.7 else "medium" if intensity > 0.4 else "low"

        return techniques[emotion_key][intensity_key]

    async def detect_cognitive_distortions(self, message: str) -> Dict[str, Any]:
        """Detect cognitive distortions in user's thinking"""

        system_prompt = """
Jesteś ekspertem od CBT. Przeanalizuj wypowiedź użytkownika pod kątem zniekształceń poznawczych:

1. **All-or-Nothing Thinking** (czarno-białe myślenie)
2. **Catastrophizing** (katastrofizowanie)
3. **Mind Reading** (czytanie w myślach)
4. **Should Statements** (powinienem/muszę)
5. **Overgeneralization** (nadmierne uogólnianie)
6. **Personalization** (personalizacja)
7. **Emotional Reasoning** (wnioskowanie z emocji)

Zwróć JSON:
{
    "distortions_found": ["nazwa zniekształcenia"],
    "examples": ["fragment wypowiedzi pokazujący zniekształcenie"],
    "reframes": ["alternatywny sposób myślenia"]
}

Jeśli nie ma zniekształceń, zwróć puste listy.
"""

        try:
            response = await self._call_llm(
                prompt=f"Wypowiedź użytkownika: {message}",
                system_prompt=system_prompt
            )

            import json
            return json.loads(response)

        except Exception as e:
            logger.error(f"Cognitive distortion detection error: {e}")
            return {"distortions_found": [], "examples": [], "reframes": []}

    async def get_mood_patterns(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Analyze mood patterns over time"""

        if not self.memory_manager:
            return {}

        try:
            # Get mood history from MongoDB
            stats = await self.memory_manager.get_mood_statistics(user_id, days=days)

            if not stats or stats.get("total_entries") == 0:
                return {"pattern": "insufficient_data"}

            # Analyze patterns
            patterns = {
                "trending": "stable",
                "most_common": stats.get("most_common_mood"),
                "average_intensity": stats.get("average_intensity"),
                "days_analyzed": days,
                "total_entries": stats.get("total_entries"),
                "recommendations": []
            }

            # Add pattern-based recommendations
            if stats.get("average_intensity", 5) < 4:
                patterns["trending"] = "declining"
                patterns["recommendations"].append(
                    "Zauważam spadek energii emocjonalnej. Rozważ rozmowę ze specjalistą lub zwiększenie aktywności fizycznej."
                )
            elif stats.get("average_intensity", 5) > 7:
                patterns["trending"] = "improving"
                patterns["recommendations"].append(
                    "Twój nastrój się poprawia! Kontynuuj to co działa."
                )

            return patterns

        except Exception as e:
            logger.error(f"Pattern analysis error: {e}")
            return {"pattern": "error", "message": str(e)}

    async def can_handle(self, message: str, context: Dict) -> float:
        """Check if this agent should handle the message"""

        emotional_keywords = [
            "czuję", "emocje", "nastrój", "smutek", "radość", "stres",
            "niepokój", "lęk", "depresja", "szczęście", "płaczę", "boi",
            "worry", "anxious", "sad", "happy", "mood", "feel", "emotion"
        ]

        message_lower = message.lower()
        matches = sum(1 for keyword in emotional_keywords if keyword in message_lower)

        return min(matches * 0.4, 1.0)
