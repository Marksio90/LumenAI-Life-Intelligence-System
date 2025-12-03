"""
Finance Agent - Budget tracking, expense management, and financial advice
"""

from typing import Dict, Any, Optional, List
from loguru import logger
from datetime import datetime, timedelta
import json

from backend.agents.base import BaseAgent


class FinanceAgent(BaseAgent):
    """
    Specialized agent for financial management
    - Budget tracking and planning
    - Expense categorization and analysis
    - Savings goals
    - Financial advice and tips
    - Spending insights
    """

    def __init__(self, memory_manager=None):
        super().__init__(
            name="Finance",
            description="Zarządzanie finansami, budżet, wydatki i oszczędności",
            memory_manager=memory_manager
        )

        # Expense categories
        self.categories = {
            "jedzenie": ["restauracja", "zakupy spożywcze", "jedzenie", "food", "groceries"],
            "transport": ["paliwo", "benzyna", "autobus", "metro", "uber", "taxi", "transport"],
            "dom": ["czynsz", "rachunki", "energia", "woda", "internet", "rent", "utilities"],
            "rozrywka": ["kino", "gry", "koncert", "hobby", "entertainment", "netflix"],
            "zdrowie": ["lekarstwa", "lekarz", "apteka", "health", "medical"],
            "ubrania": ["odzież", "buty", "clothes", "fashion"],
            "edukacja": ["książki", "kursy", "szkolenia", "education", "books"],
            "inne": []
        }

    async def process(
        self,
        user_id: str,
        message: str,
        context: Dict[str, Any],
        metadata: Optional[Dict] = None
    ) -> str:
        """Process finance-related requests"""

        logger.info(f"Finance Agent processing for {user_id}")

        # Determine request type
        request_type = await self._classify_request(message)

        if request_type == "add_expense":
            return await self._add_expense(user_id, message, context)
        elif request_type == "budget_overview":
            return await self._get_budget_overview(user_id, context)
        elif request_type == "spending_analysis":
            return await self._analyze_spending(user_id, message, context)
        elif request_type == "savings_goal":
            return await self._manage_savings_goal(user_id, message, context)
        elif request_type == "financial_advice":
            return await self._provide_financial_advice(user_id, message, context)
        else:
            return await self._general_finance_help(message, context)

    async def _classify_request(self, message: str) -> str:
        """Classify type of financial request"""

        message_lower = message.lower()

        # Add expense indicators
        if any(word in message_lower for word in [
            "wydałem", "zapłaciłem", "kupiłem", "koszt", "dodaj wydatek",
            "spent", "paid", "bought", "add expense"
        ]):
            return "add_expense"

        # Budget overview
        if any(word in message_lower for word in [
            "budżet", "ile wydałem", "podsumowanie", "wydatki",
            "budget", "how much", "summary", "expenses"
        ]):
            return "budget_overview"

        # Spending analysis
        if any(word in message_lower for word in [
            "analiza", "na co", "gdzie wydaję", "kategorie",
            "analysis", "where", "categories", "breakdown"
        ]):
            return "spending_analysis"

        # Savings goal
        if any(word in message_lower for word in [
            "oszczędności", "cel", "odkładam", "chcę zaoszczędzić",
            "savings", "goal", "save", "saving"
        ]):
            return "savings_goal"

        # Financial advice
        if any(word in message_lower for word in [
            "rada", "porada", "jak", "powinienem", "inwestować",
            "advice", "should", "invest", "recommend"
        ]):
            return "financial_advice"

        return "general"

    async def _add_expense(self, user_id: str, message: str, context: Dict) -> str:
        """Add expense entry"""

        system_prompt = """
Jesteś asystentem finansowym. Użytkownik chce dodać wydatek.

Z wiadomości wydobądź:
1. Kwotę wydatku (w PLN)
2. Kategorię (jedzenie, transport, dom, rozrywka, zdrowie, ubrania, edukacja, inne)
3. Opis wydatku
4. Datę (jeśli podana, inaczej dzisiaj)

Odpowiedz w formacie JSON:
{
  "amount": 50.0,
  "category": "jedzenie",
  "description": "lunch w restauracji",
  "date": "2025-12-03",
  "success": true
}

Jeśli nie ma wystarczających informacji, ustaw success: false i zapytaj o brakujące dane.
"""

        llm_response = await self._call_llm(message, system_prompt)

        try:
            expense_data = json.loads(llm_response)

            if not expense_data.get("success"):
                return "❓ Potrzebuję więcej informacji. Powiedz mi ile wydałeś i na co?"

            # Store in memory (this would typically go to database)
            if self.memory_manager:
                await self.memory_manager.store_user_context(
                    user_id=user_id,
                    context_type="expense",
                    key=f"expense_{datetime.now().timestamp()}",
                    value=expense_data,
                    source="finance_agent"
                )

            amount = expense_data.get("amount", 0)
            category = expense_data.get("category", "inne")
            description = expense_data.get("description", "")

            return f"""💰 **Wydatek dodany!**

**Kwota:** {amount} PLN
**Kategoria:** {category.capitalize()}
**Opis:** {description}

Zapisałem w Twoim budżecie. Chcesz zobaczyć podsumowanie wydatków?
"""

        except json.JSONDecodeError:
            return "✅ Zapisałem Twój wydatek! Potrzebujesz czegoś jeszcze?"

    async def _get_budget_overview(self, user_id: str, context: Dict) -> str:
        """Get budget overview and summary"""

        # In production, this would fetch from database
        # For now, we'll generate a helpful response

        system_prompt = """
Jesteś asystentem finansowym. Użytkownik pyta o swój budżet.

Wygeneruj pomocną odpowiedź z:
1. Sugestią jak śledzić wydatki
2. Pytaniem o miesięczny budżet
3. Informacją o kategoriach które śledzimy
4. Zachętą do dodawania wydatków

Bądź przyjazny i motywujący.
"""

        response = await self._call_llm(
            "Pokaż mi mój budżet i wydatki",
            system_prompt
        )

        return f"📊 **Twój Budżet**\n\n{response}"

    async def _analyze_spending(self, user_id: str, message: str, context: Dict) -> str:
        """Analyze spending patterns"""

        system_prompt = """
Jesteś ekspertem od analizy finansowej.

Pomóż użytkownikowi zrozumieć jego wzorce wydatków:
1. Zasugeruj śledzenie wydatków przez kategorie
2. Zaproponuj użyteczne metryki (wydatki dzienne, tygodniowe, miesięczne)
3. Wskaż typowe kategorie gdzie ludzie wydają najwięcej
4. Daj praktyczne porady jak kontrolować wydatki

Odpowiedz w sposób angażujący i pomocny.
"""

        response = await self._call_llm(message, system_prompt)

        return f"📈 **Analiza Wydatków**\n\n{response}"

    async def _manage_savings_goal(self, user_id: str, message: str, context: Dict) -> str:
        """Manage savings goals"""

        system_prompt = """
Pomóż użytkownikowi z celami oszczędnościowymi.

Z wiadomości określ:
- Jaki cel oszczędnościowy (kwota, cel)
- W jakim czasie chce osiągnąć
- Ile może odkładać miesięcznie

Oblicz:
- Ile musi odkładać miesięcznie/tygodniowo
- Kiedy osiągnie cel
- Praktyczne porady jak oszczędzać

Bądź konkretny i motywujący.
"""

        response = await self._call_llm(message, system_prompt)

        return f"🎯 **Twój Cel Oszczędnościowy**\n\n{response}"

    async def _provide_financial_advice(self, user_id: str, message: str, context: Dict) -> str:
        """Provide financial advice"""

        system_prompt = """
Jesteś mądrym doradcą finansowym.

Zasady dobrej porady:
- Oparta na zdrowym rozsądku
- Dostosowana do sytuacji użytkownika
- Praktyczna i wykonalna
- Bezpieczna (nie spekulacyjna)

Tematy:
- Budżetowanie (50/30/20 rule)
- Fundusz awaryjny
- Kontrola wydatków
- Oszczędzanie
- Podstawy inwestowania (dla zainteresowanych)

Unikaj:
- Konkretnych rekomendacji inwestycyjnych
- Obietnic zysków
- Złożonych instrumentów finansowych

Mów jasno i zrozumiale po polsku.
"""

        response = await self._call_llm(message, system_prompt)

        return f"💡 **Porada Finansowa**\n\n{response}"

    async def _general_finance_help(self, message: str, context: Dict) -> str:
        """General financial help"""

        system_prompt = """
Jesteś asystentem finansowym LumenAI.

Pomóż użytkownikowi z finansami:
- Budżetowanie
- Śledzenie wydatków
- Cele oszczędnościowe
- Porady finansowe

Odpowiadaj w sposób praktyczny, jasny i pomocny.
"""

        response = await self._call_llm(message, system_prompt)

        return response

    async def can_handle(self, message: str, context: Dict) -> float:
        """Check if this agent should handle the message"""

        finance_keywords = [
            "pieniądze", "budżet", "wydatki", "oszczędności", "koszty",
            "wydałem", "zapłaciłem", "kupiłem", "finanse", "money",
            "budget", "expenses", "savings", "spent", "paid", "cost"
        ]

        message_lower = message.lower()
        matches = sum(1 for keyword in finance_keywords if keyword in message_lower)

        return min(matches * 0.35, 1.0)
