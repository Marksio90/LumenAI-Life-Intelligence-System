"""
Automation Agent - External integrations and task automation
"""

from typing import Dict, Any, Optional, List
from loguru import logger
import json
from datetime import datetime

from agents.base import BaseAgent


class AutomationAgent(BaseAgent):
    """
    Specialized agent for automation and integrations
    - Email sending
    - Calendar management (Google Calendar, Outlook)
    - Note creation (Notion, Evernote)
    - Task management (Todoist, Trello)
    - Webhooks and API calls
    - File operations
    """

    def __init__(self, memory_manager=None, llm_engine=None):
        super().__init__(
            name="Automation",
            description="Automatyzacja zadań, integracje z zewnętrznymi API",
            memory_manager=memory_manager,
            llm_engine=llm_engine
        )

        # Available integrations (would be configured via env vars in production)
        self.available_integrations = {
            "email": False,  # SMTP/Gmail API
            "google_calendar": False,  # Google Calendar API
            "notion": False,  # Notion API
            "todoist": False,  # Todoist API
            "slack": False,  # Slack API
            "github": False,  # GitHub API
            "webhooks": True,  # Generic webhooks (always available)
        }

    async def process(
        self,
        user_id: str,
        message: str,
        context: Dict[str, Any],
        metadata: Optional[Dict] = None
    ) -> str:
        """Process automation requests"""

        logger.info(f"Automation Agent processing for {user_id}")

        # Determine automation type
        automation_type = await self._classify_automation(message)

        if automation_type == "send_email":
            return await self._send_email(user_id, message, context)
        elif automation_type == "calendar_event":
            return await self._manage_calendar(user_id, message, context)
        elif automation_type == "create_note":
            return await self._create_note(user_id, message, context)
        elif automation_type == "task_management":
            return await self._manage_task(user_id, message, context)
        elif automation_type == "webhook":
            return await self._execute_webhook(user_id, message, context)
        else:
            return await self._general_automation_help(message, context)

    async def _classify_automation(self, message: str) -> str:
        """Classify type of automation request"""

        message_lower = message.lower()

        # Email indicators
        if any(word in message_lower for word in [
            "wyślij email", "wyślij maila", "napisz email", "send email",
            "email to", "mail to"
        ]):
            return "send_email"

        # Calendar indicators
        if any(word in message_lower for word in [
            "dodaj do kalendarza", "zaplanuj spotkanie", "event", "calendar",
            "spotkanie w", "reminder", "appointment"
        ]):
            return "calendar_event"

        # Note creation
        if any(word in message_lower for word in [
            "stwórz notatkę", "zapisz w notion", "create note", "add to notion",
            "note", "notatka"
        ]):
            return "create_note"

        # Task management
        if any(word in message_lower for word in [
            "dodaj zadanie", "todoist", "trello", "add task", "create task",
            "todo"
        ]):
            return "task_management"

        # Webhook
        if any(word in message_lower for word in [
            "webhook", "api call", "trigger", "wywołaj"
        ]):
            return "webhook"

        return "general"

    async def _send_email(self, user_id: str, message: str, context: Dict) -> str:
        """Send email (placeholder for now)"""

        if not self.available_integrations.get("email"):
            return """📧 **Wysyłanie emaili**

Funkcja wysyłania emaili wymaga konfiguracji:
1. Podłącz swoje konto Gmail/SMTP
2. Nadaj uprawnienia aplikacji
3. Będę mógł wysyłać maile w Twoim imieniu!

Na razie mogę pomóc Ci skomponować treść emaila. Powiedz mi:
- Do kogo chcesz wysłać
- Jaki ma być temat
- Co chcesz napisać
"""

        system_prompt = """
Pomóż użytkownikowi skomponować emaila.

Wydobądź z wiadomości:
1. Odbiorcę (email address)
2. Temat
3. Treść
4. Ton (formalny/nieformalny)

Jeśli czegoś brakuje, zapytaj o to.

Zaproponuj dobrze sformatowaną treść emaila.
"""

        response = await self._call_llm(message, system_prompt)

        return f"✍️ **Projekt Emaila**\n\n{response}\n\n---\n💡 Aby naprawdę wysłać email, podłącz swoje konto w ustawieniach."

    async def _manage_calendar(self, user_id: str, message: str, context: Dict) -> str:
        """Manage calendar events"""

        if not self.available_integrations.get("google_calendar"):
            return """📅 **Integracja z Kalendarzem**

Aby dodawać wydarzenia do kalendarza, podłącz:
- Google Calendar
- Outlook Calendar
- iCloud Calendar

Na razie mogę pomóc Ci zaplanować wydarzenie. Powiedz mi:
- Co chcesz zaplanować
- Kiedy (data i godzina)
- Jak długo
- Czy ktoś ma być zaproszony
"""

        system_prompt = """
Pomóż użytkownikowi zaplanować wydarzenie.

Wydobądź:
1. Tytuł wydarzenia
2. Data i czas rozpoczęcia
3. Czas trwania
4. Lokalizacja (jeśli jest)
5. Uczestnicy (jeśli są)
6. Opis

Sformatuj to jako gotowe wydarzenie kalendarzowe.
"""

        response = await self._call_llm(message, system_prompt)

        return f"🗓️ **Planowane Wydarzenie**\n\n{response}\n\n---\n💡 Podłącz kalendarz, aby automatycznie dodawać wydarzenia!"

    async def _create_note(self, user_id: str, message: str, context: Dict) -> str:
        """Create note in external service"""

        if not self.available_integrations.get("notion"):
            return """📝 **Tworzenie Notatek**

Mogę tworzyć notatki w:
- Notion
- Evernote
- OneNote
- Google Keep

Podłącz swoje konto, a będę mógł zapisywać notatki automatycznie!

Na razie mogę pomóc Ci sformatować notatkę. Co chcesz zapisać?
"""

        system_prompt = """
Pomóż użytkownikowi stworzyć notatkę.

Sformatuj notatkę z:
1. Tytułem
2. Treścią (dobrze sformatowaną)
3. Tagami/kategoriami
4. Datą

Użyj Markdown dla formatowania.
"""

        response = await self._call_llm(message, system_prompt)

        return f"📄 **Notatka**\n\n{response}\n\n---\n💡 Podłącz Notion lub Evernote, aby zapisać!"

    async def _manage_task(self, user_id: str, message: str, context: Dict) -> str:
        """Manage tasks in external services"""

        if not self.available_integrations.get("todoist"):
            return """✅ **Zarządzanie Zadaniami**

Mogę zarządzać zadaniami w:
- Todoist
- Trello
- Asana
- Microsoft To Do

Podłącz swoje narzędzie, a będę mógł:
- Dodawać zadania
- Ustawiać terminy
- Oznaczać priorytet
- Kategoryzować

Na razie mogę pomóc Ci zaplanować zadanie. Co trzeba zrobić?
"""

        system_prompt = """
Pomóż użytkownikowi stworzyć zadanie.

Określ:
1. Nazwa zadania
2. Opis
3. Termin wykonania
4. Priorytet (niski/średni/wysoki)
5. Projekt/kategoria

Sformatuj jako gotowe zadanie.
"""

        response = await self._call_llm(message, system_prompt)

        return f"📋 **Zadanie**\n\n{response}\n\n---\n💡 Podłącz Todoist lub Trello, aby synchronizować!"

    async def _execute_webhook(self, user_id: str, message: str, context: Dict) -> str:
        """Execute webhook or API call"""

        system_prompt = """
Użytkownik chce wywołać webhook lub API.

Pomóż mu skonfigurować:
1. URL endpointa
2. Metodę HTTP (GET/POST/PUT/DELETE)
3. Headers
4. Body/payload
5. Authentication

Wytłumacz krok po kroku co trzeba zrobić.
"""

        response = await self._call_llm(message, system_prompt)

        return f"🔗 **Konfiguracja Webhooka**\n\n{response}\n\n---\n⚠️ Upewnij się, że webhook jest bezpieczny i zaufany!"

    async def _general_automation_help(self, message: str, context: Dict) -> str:
        """General automation help"""

        system_prompt = """
Jesteś agentem automatyzacji LumenAI.

Możesz pomóc z:
- Wysyłaniem emaili
- Zarządzaniem kalendarzem
- Tworzeniem notatek
- Zarządzaniem zadaniami
- Integracjami API
- Automatyzacją powtarzalnych czynności

Pomóż użytkownikowi z jego prośbą. Jeśli wymaga integracji:
1. Wyjaśnij co można zautomatyzować
2. Jakie integracje są potrzebne
3. Jak je skonfigurować
4. Jakie korzyści przyniesie

Bądź praktyczny i pomocny.
"""

        response = await self._call_llm(message, system_prompt)

        return f"🤖 **Automatyzacja**\n\n{response}\n\n---\n\n**Dostępne integracje:**\n" + \
               "\n".join([f"{'✅' if enabled else '⚪'} {name.replace('_', ' ').title()}"
                         for name, enabled in self.available_integrations.items()])

    async def setup_integration(
        self,
        integration_name: str,
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Setup external integration (for future use)

        Args:
            integration_name: Name of integration (e.g., 'gmail', 'notion')
            credentials: API keys, tokens, etc.

        Returns:
            Setup status and details
        """

        # This would be implemented to actually configure integrations
        # For now, it's a placeholder

        return {
            "success": False,
            "message": "Integration setup not yet implemented",
            "integration": integration_name
        }

    async def can_handle(self, message: str, context: Dict) -> float:
        """Check if this agent should handle the message"""

        automation_keywords = [
            "wyślij", "send", "email", "mail", "kalendarz", "calendar",
            "notatka", "note", "notion", "zadanie", "task", "todoist",
            "webhook", "api", "automatyzacja", "automation", "integracja",
            "integration", "trigger", "wykonaj"
        ]

        message_lower = message.lower()
        matches = sum(1 for keyword in automation_keywords if keyword in message_lower)

        return min(matches * 0.3, 0.9)
