"""
Google Calendar Integration Service
Handles authentication and operations with Google Calendar API
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import os

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger.warning("Google Calendar libraries not installed. Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")


# If modifying these scopes, delete the token file
SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarService:
    """
    Service for interacting with Google Calendar API
    """

    def __init__(self, credentials_path: str = None, token_path: str = None):
        """
        Initialize Google Calendar service

        Args:
            credentials_path: Path to credentials.json from Google Cloud Console
            token_path: Path to store authentication token
        """
        if not GOOGLE_AVAILABLE:
            logger.error("Google Calendar integration not available - missing dependencies")
            self.service = None
            return

        self.credentials_path = credentials_path or os.getenv(
            'GOOGLE_CREDENTIALS_PATH',
            'backend/data/google_credentials.json'
        )
        self.token_path = token_path or os.getenv(
            'GOOGLE_TOKEN_PATH',
            'backend/data/google_token.json'
        )
        self.service = None

    async def authenticate(self) -> bool:
        """
        Authenticate with Google Calendar API

        Returns:
            True if authentication successful
        """
        if not GOOGLE_AVAILABLE:
            logger.error("Cannot authenticate - Google libraries not available")
            return False

        try:
            creds = None

            # Load token if exists
            if os.path.exists(self.token_path):
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

            # If no valid credentials, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        logger.error(f"Google credentials not found at {self.credentials_path}")
                        logger.info("Download credentials.json from Google Cloud Console")
                        return False

                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save credentials for next run
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())

            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("✅ Google Calendar authenticated successfully")
            return True

        except Exception as e:
            logger.error(f"Google Calendar authentication failed: {e}")
            return False

    async def list_calendars(self) -> List[Dict[str, Any]]:
        """
        List all available calendars

        Returns:
            List of calendar objects
        """
        if not self.service:
            await self.authenticate()

        if not self.service:
            return []

        try:
            calendar_list = self.service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])

            return [
                {
                    'id': cal['id'],
                    'name': cal['summary'],
                    'primary': cal.get('primary', False),
                    'color': cal.get('backgroundColor', '#000000')
                }
                for cal in calendars
            ]

        except HttpError as e:
            logger.error(f"Error listing calendars: {e}")
            return []

    async def get_events(
        self,
        calendar_id: str = 'primary',
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get events from calendar

        Args:
            calendar_id: Calendar ID (default: 'primary')
            time_min: Minimum time for events
            time_max: Maximum time for events
            max_results: Maximum number of events

        Returns:
            List of event objects
        """
        if not self.service:
            await self.authenticate()

        if not self.service:
            return []

        try:
            # Default to today if no time specified
            if not time_min:
                time_min = datetime.utcnow()
            if not time_max:
                time_max = time_min + timedelta(days=7)

            # Format times for API
            time_min_str = time_min.isoformat() + 'Z'
            time_max_str = time_max.isoformat() + 'Z'

            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min_str,
                timeMax=time_max_str,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            # Format events
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))

                formatted_events.append({
                    'id': event['id'],
                    'summary': event.get('summary', 'Untitled Event'),
                    'description': event.get('description', ''),
                    'start': start,
                    'end': end,
                    'location': event.get('location', ''),
                    'attendees': event.get('attendees', []),
                    'link': event.get('htmlLink', '')
                })

            return formatted_events

        except HttpError as e:
            logger.error(f"Error getting events: {e}")
            return []

    async def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: str = "",
        location: str = "",
        attendees: List[str] = None,
        calendar_id: str = 'primary'
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new event in calendar

        Args:
            summary: Event title
            start_time: Event start time
            end_time: Event end time
            description: Event description
            location: Event location
            attendees: List of attendee emails
            calendar_id: Calendar ID

        Returns:
            Created event object or None if failed
        """
        if not self.service:
            await self.authenticate()

        if not self.service:
            return None

        try:
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'Europe/Warsaw',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'Europe/Warsaw',
                },
            }

            if location:
                event['location'] = location

            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]

            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()

            logger.info(f"✅ Created event: {summary} at {start_time}")

            return {
                'id': created_event['id'],
                'summary': created_event['summary'],
                'start': created_event['start']['dateTime'],
                'end': created_event['end']['dateTime'],
                'link': created_event.get('htmlLink', '')
            }

        except HttpError as e:
            logger.error(f"Error creating event: {e}")
            return None

    async def update_event(
        self,
        event_id: str,
        calendar_id: str = 'primary',
        **updates
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing event

        Args:
            event_id: Event ID
            calendar_id: Calendar ID
            **updates: Fields to update

        Returns:
            Updated event or None
        """
        if not self.service:
            await self.authenticate()

        if not self.service:
            return None

        try:
            # Get current event
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

            # Apply updates
            for key, value in updates.items():
                if key in ['start', 'end'] and isinstance(value, datetime):
                    event[key] = {
                        'dateTime': value.isoformat(),
                        'timeZone': 'Europe/Warsaw',
                    }
                else:
                    event[key] = value

            # Update event
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()

            logger.info(f"✅ Updated event: {event_id}")
            return updated_event

        except HttpError as e:
            logger.error(f"Error updating event: {e}")
            return None

    async def delete_event(
        self,
        event_id: str,
        calendar_id: str = 'primary'
    ) -> bool:
        """
        Delete an event

        Args:
            event_id: Event ID
            calendar_id: Calendar ID

        Returns:
            True if deleted successfully
        """
        if not self.service:
            await self.authenticate()

        if not self.service:
            return False

        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

            logger.info(f"✅ Deleted event: {event_id}")
            return True

        except HttpError as e:
            logger.error(f"Error deleting event: {e}")
            return False

    async def get_free_busy(
        self,
        time_min: datetime,
        time_max: datetime,
        calendar_ids: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get free/busy information for calendars

        Args:
            time_min: Start time
            time_max: End time
            calendar_ids: List of calendar IDs (default: primary)

        Returns:
            Free/busy data
        """
        if not self.service:
            await self.authenticate()

        if not self.service:
            return {}

        if not calendar_ids:
            calendar_ids = ['primary']

        try:
            body = {
                "timeMin": time_min.isoformat() + 'Z',
                "timeMax": time_max.isoformat() + 'Z',
                "items": [{"id": cal_id} for cal_id in calendar_ids]
            }

            response = self.service.freebusy().query(body=body).execute()
            return response.get('calendars', {})

        except HttpError as e:
            logger.error(f"Error getting free/busy: {e}")
            return {}

    async def get_today_schedule(self) -> str:
        """
        Get formatted schedule for today

        Returns:
            Formatted string with today's events
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        events = await self.get_events(
            time_min=today,
            time_max=tomorrow,
            max_results=20
        )

        if not events:
            return "📅 Brak wydarzeń na dzisiaj! Masz wolny dzień 🎉"

        schedule = f"📅 **Twój plan na {today.strftime('%A, %d %B')}:**\n\n"

        for event in events:
            start_time = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
            schedule += f"⏰ **{start_time.strftime('%H:%M')}** - {event['summary']}\n"

            if event.get('location'):
                schedule += f"   📍 {event['location']}\n"

            if event.get('description'):
                schedule += f"   📝 {event['description'][:100]}...\n" if len(event['description']) > 100 else f"   📝 {event['description']}\n"

            schedule += "\n"

        return schedule
