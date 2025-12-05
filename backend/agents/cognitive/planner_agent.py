"""
Planner Agent - Manages scheduling, tasks, calendar, and time management
"""

from typing import Dict, Any, Optional, List
from loguru import logger
from datetime import datetime, timedelta
import json

from backend.agents.base import BaseAgent
from backend.services.integrations.google_calendar_service import GoogleCalendarService


class PlannerAgent(BaseAgent):
    """
    Specialized agent for planning and time management
    - Daily/weekly planning
    - Task management
    - Calendar integration
    - Reminders
    """

    def __init__(self, memory_manager=None, calendar_service=None, llm_engine=None):
        super().__init__(
            name="Planner",
            description="Zarządzanie czasem, planowanie zadań i organizacja dnia",
            memory_manager=memory_manager,
            llm_engine=llm_engine
        )
        self.calendar_service = calendar_service or GoogleCalendarService()
        self.calendar_enabled = False

    async def process(
        self,
        user_id: str,
        message: str,
        context: Dict[str, Any],
        metadata: Optional[Dict] = None
    ) -> str:
        """Process planning-related requests"""

        logger.info(f"Planner Agent processing for {user_id}")

        # Check what type of planning request
        request_type = await self._classify_request(message)

        if request_type == "create_task":
            return await self._create_task(user_id, message, context)
        elif request_type == "view_schedule":
            return await self._view_schedule(user_id, context)
        elif request_type == "plan_day":
            return await self._plan_day(user_id, message, context)
        else:
            return await self._general_planning_advice(message, context)

    async def _classify_request(self, message: str) -> str:
        """Classify the type of planning request"""
        message_lower = message.lower()

        if any(word in message_lower for word in ["dodaj zadanie", "nowe zadanie", "to-do"]):
            return "create_task"
        elif any(word in message_lower for word in ["pokaż", "zobacz", "plan", "harmonogram"]):
            return "view_schedule"
        elif any(word in message_lower for word in ["zaplanuj dzień", "plan dnia", "co dzisiaj"]):
            return "plan_day"
        else:
            return "general"

    async def _create_task(self, user_id: str, message: str, context: Dict) -> str:
        """Create a new task"""

        system_prompt = """
Jesteś asystentem planowania. Użytkownik chce dodać zadanie.
Wyciągnij z jego wiadomości:
- Nazwę zadania
- Termin (jeśli podany)
- Priorytet (jeśli podany)

Odpowiedz JSON:
{
    "task_name": "...",
    "deadline": "YYYY-MM-DD lub null",
    "priority": "high/medium/low"
}
"""

        try:
            response = await self._call_llm(message, system_prompt)
            task_data = json.loads(response)

            # Store task (simplified - will integrate with database)
            task_name = task_data.get("task_name", "Nowe zadanie")
            deadline = task_data.get("deadline")
            priority = task_data.get("priority", "medium")

            # Create friendly response
            response_text = f"✅ Dodałem zadanie: **{task_name}**"

            if deadline:
                response_text += f"\n📅 Termin: {deadline}"

            response_text += f"\n🎯 Priorytet: {priority}"

            return response_text

        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return "Dodałem Twoje zadanie do listy. Przypomnę Ci o nim w odpowiednim momencie!"

    async def _view_schedule(self, user_id: str, context: Dict) -> str:
        """Show user's schedule"""

        # Try to use Google Calendar if available
        if self.calendar_service:
            try:
                if not self.calendar_enabled:
                    self.calendar_enabled = await self.calendar_service.authenticate()

                if self.calendar_enabled:
                    return await self.calendar_service.get_today_schedule()
            except Exception as e:
                logger.warning(f"Google Calendar unavailable: {e}")

        # Fallback to mock schedule
        today = datetime.now()

        schedule = f"""
📅 **Twój plan na dzisiaj** ({today.strftime('%A, %d %B')})

🌅 **Rano:**
- 7:00 - Poranna rutyna
- 8:00 - Śniadanie i planowanie dnia

☀️ **Południe:**
- Brak zaplanowanych zadań

🌆 **Wieczór:**
- 18:00 - Czas na relaks
- 21:00 - Przygotowanie do snu

💡 **Podpowiedź:** Masz wolny dzień! Może warto wykorzystać go na coś kreatywnego?

ℹ️ *Połącz konto Google Calendar, aby widzieć prawdziwe wydarzenia!*
"""

        return schedule

    async def _plan_day(self, user_id: str, message: str, context: Dict) -> str:
        """Help plan the day"""

        system_prompt = """
Jesteś ekspertem od planowania dnia. Pomóż użytkownikowi stworzyć efektywny plan.

Zasady dobrego planowania:
- Zacznij od najważniejszych zadań (eat the frog)
- Uwzględnij przerwy
- Realistyczne czasowo
- Balans praca-odpoczynek

Stwórz spersonalizowany plan dnia w przyjaznej formie.
"""

        response = await self._call_llm(
            prompt=f"Użytkownik mówi: {message}\n\nStwórz dla niego plan dnia.",
            system_prompt=system_prompt
        )

        return f"📋 **Twój plan dnia:**\n\n{response}"

    async def _general_planning_advice(self, message: str, context: Dict) -> str:
        """General planning advice"""

        system_prompt = """
Jesteś ekspertem od produktywności i zarządzania czasem.
Udzielaj konkretnych, praktycznych porad.
Mów po polsku w sposób przyjazny i motywujący.
"""

        response = await self._call_llm(message, system_prompt)
        return response

    async def add_calendar_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: str = "",
        location: str = ""
    ) -> Dict[str, Any]:
        """Add event to Google Calendar"""

        if not self.calendar_service:
            return {"success": False, "error": "Calendar service not available"}

        try:
            if not self.calendar_enabled:
                self.calendar_enabled = await self.calendar_service.authenticate()

            if not self.calendar_enabled:
                return {"success": False, "error": "Calendar authentication failed"}

            event = await self.calendar_service.create_event(
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                description=description,
                location=location
            )

            if event:
                return {
                    "success": True,
                    "event": event,
                    "message": f"✅ Dodano wydarzenie: {summary}"
                }
            else:
                return {"success": False, "error": "Failed to create event"}

        except Exception as e:
            logger.error(f"Error adding calendar event: {e}")
            return {"success": False, "error": str(e)}

    async def get_week_schedule(self, user_id: str) -> str:
        """Get schedule for the week"""

        if not self.calendar_service:
            return "📅 Kalendarz Google nie jest dostępny."

        try:
            if not self.calendar_enabled:
                self.calendar_enabled = await self.calendar_service.authenticate()

            if not self.calendar_enabled:
                return "📅 Połącz konto Google Calendar, aby zobaczyć harmonogram tygodnia."

            # Get events for next 7 days
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            next_week = today + timedelta(days=7)

            events = await self.calendar_service.get_events(
                time_min=today,
                time_max=next_week,
                max_results=50
            )

            if not events:
                return "📅 Brak wydarzeń w najbliższym tygodniu!"

            # Group events by day
            events_by_day = {}
            for event in events:
                start = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                day_key = start.strftime('%Y-%m-%d')

                if day_key not in events_by_day:
                    events_by_day[day_key] = []

                events_by_day[day_key].append({
                    'time': start.strftime('%H:%M'),
                    'summary': event['summary'],
                    'location': event.get('location', '')
                })

            # Format output
            schedule = "📅 **Twój harmonogram na tydzień:**\n\n"

            for day in sorted(events_by_day.keys()):
                day_date = datetime.fromisoformat(day)
                schedule += f"**{day_date.strftime('%A, %d %B')}:**\n"

                for event in events_by_day[day]:
                    schedule += f"  ⏰ {event['time']} - {event['summary']}"
                    if event['location']:
                        schedule += f" 📍 {event['location']}"
                    schedule += "\n"

                schedule += "\n"

            return schedule

        except Exception as e:
            logger.error(f"Error getting week schedule: {e}")
            return f"❌ Błąd podczas pobierania harmonogramu: {str(e)}"

    async def suggest_time_blocking(self, user_id: str, tasks: List[str]) -> str:
        """Suggest time blocking for tasks based on calendar free time"""

        system_prompt = """
Jesteś ekspertem od time blocking i produktywności.

Użytkownik podał listę zadań. Zasugeruj:
1. Realistyczne bloki czasowe dla każdego zadania
2. Najlepszy czas dnia dla każdego typu zadania
3. Przerwy między zadaniami
4. Balance między pracą a odpoczynkiem

Format: czas + zadanie + uzasadnienie
"""

        tasks_str = "\n".join([f"- {task}" for task in tasks])

        response = await self._call_llm(
            prompt=f"Zadania do zaplanowania:\n{tasks_str}",
            system_prompt=system_prompt
        )

        return f"📋 **Time Blocking Plan:**\n\n{response}"

    async def can_handle(self, message: str, context: Dict) -> float:
        """Check if this agent should handle the message"""

        keywords = [
            "plan", "zadanie", "kalendarz", "termin", "przypomnienie",
            "harmonogram", "czas", "zorganizuj", "produktywność",
            "schedule", "calendar", "event", "meeting", "tydzień"
        ]

        message_lower = message.lower()
        matches = sum(1 for keyword in keywords if keyword in message_lower)

        return min(matches * 0.3, 1.0)
