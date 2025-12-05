"""
Decision Agent - Helps with life decisions and choices
"""

from typing import Dict, Any, Optional, List
from loguru import logger
import json

from backend.agents.base import BaseAgent


class DecisionAgent(BaseAgent):
    """
    Specialized agent for decision making and life choices
    - Analyze options
    - Pros/cons analysis
    - Decision frameworks
    - Life advice
    """

    def __init__(self, memory_manager=None, llm_engine=None):
        super().__init__(
            name="Decision",
            description="Pomoc w podejmowaniu decyzji i wyborów życiowych",
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
        """Process decision-making requests"""

        logger.info(f"Decision Agent processing for {user_id}")

        # Determine decision type
        decision_type = await self._classify_decision(message)

        if decision_type == "binary_choice":
            return await self._analyze_binary_choice(message, context)
        elif decision_type == "multiple_options":
            return await self._analyze_multiple_options(message, context)
        elif decision_type == "life_advice":
            return await self._provide_life_advice(message, context)
        else:
            return await self._general_decision_help(message, context)

    async def _classify_decision(self, message: str) -> str:
        """Classify type of decision"""

        message_lower = message.lower()

        # Binary choice indicators
        if any(word in message_lower for word in ["czy powinienem", "albo", "vs", "lub"]):
            return "binary_choice"

        # Multiple options
        if "opcje" in message_lower or "możliwości" in message_lower:
            return "multiple_options"

        # Life advice
        if any(word in message_lower for word in ["życie", "kariera", "związek", "przeprowadzka"]):
            return "life_advice"

        return "general"

    async def _analyze_binary_choice(self, message: str, context: Dict) -> str:
        """Analyze a binary choice (A or B)"""

        system_prompt = """
Pomóż użytkownikowi w decyzji między dwoma opcjami.

Użyj frameworka:
1. Zrozum obie opcje
2. Lista pros/cons każdej
3. Rozważ wartości użytkownika
4. Pytania do refleksji
5. Nie podejmuj decyzji za użytkownika - pomóż mu ją przemyśleć

Format odpowiedzi:
**Opcja A: [nazwa]**
✅ Zalety: ...
❌ Wady: ...

**Opcja B: [nazwa]**
✅ Zalety: ...
❌ Wady: ...

**Pytania do przemyślenia:**
- ...

**Moja analiza:**
...
"""

        response = await self._call_llm(
            prompt=f"Użytkownik przed decyzją: {message}",
            system_prompt=system_prompt
        )

        return f"🤔 **Analiza Twojej decyzji:**\n\n{response}"

    async def _analyze_multiple_options(self, message: str, context: Dict) -> str:
        """Analyze multiple options"""

        system_prompt = """
Pomóż użytkownikowi w wyborze spośród wielu opcji.

Użyj decision matrix:
1. Zidentyfikuj wszystkie opcje
2. Określ kryteria decyzyjne
3. Oceń każdą opcję według kryteriów
4. Rekomendacja oparta na analizie

Bądź systematyczny i klarowny.
"""

        response = await self._call_llm(message, system_prompt)
        return f"📊 **Analiza opcji:**\n\n{response}"

    async def _provide_life_advice(self, message: str, context: Dict) -> str:
        """Provide life advice"""

        system_prompt = """
Jesteś mądrym doradcą życiowym.

Cechy dobrej porady:
- Empatyczna, ale szczera
- Perspektywa długoterminowa
- Uwzględniaj wartości i cele użytkownika
- Praktyczne kroki działania
- Zachęta do samodzielnego myślenia

Unikaj:
- Narzucania swojej wizji
- Banałów i ogólników
- Moralizowania

Bądź autentyczny i pomocny.
"""

        response = await self._call_llm(message, system_prompt)
        return f"💭 **Refleksja:**\n\n{response}"

    async def _general_decision_help(self, message: str, context: Dict) -> str:
        """General decision-making help"""

        system_prompt = """
Pomóż użytkownikowi w podejmowaniu decyzji.

Techniki:
- Stawianie właściwych pytań
- Identyfikacja wartości
- Analiza konsekwencji
- Rozważenie alternatyw

Prowadź użytkownika do jego własnej odpowiedzi.
"""

        response = await self._call_llm(message, system_prompt)
        return response

    def create_decision_matrix(
        self,
        options: List[str],
        criteria: List[str],
        weights: Optional[Dict[str, float]] = None
    ) -> Dict:
        """Create a decision matrix for structured analysis"""

        matrix = {
            "options": options,
            "criteria": criteria,
            "weights": weights or {c: 1.0 for c in criteria},
            "scores": {}
        }

        return matrix

    async def can_handle(self, message: str, context: Dict) -> float:
        """Check if this agent should handle the message"""

        decision_keywords = [
            "decyzja", "wybór", "czy powinienem", "pomóż zdecydować",
            "nie wiem co", "opcje", "rada", "co zrobić", "dilema"
        ]

        message_lower = message.lower()
        matches = sum(1 for keyword in decision_keywords if keyword in message_lower)

        return min(matches * 0.35, 1.0)
