"""
Enhanced Google Calendar Service
Improved error handling, caching, and batch operations
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import asyncio

from services.integrations.google_calendar_service import GoogleCalendarService
from services.performance_optimizer import cached, rate_limit


class EnhancedCalendarService(GoogleCalendarService):
    """
    Enhanced Google Calendar service with performance optimizations
    """

    def __init__(self):
        super().__init__()
        self.health_status = {
            "last_sync": None,
            "total_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0
        }

    @cached(ttl=300)  # Cache for 5 minutes
    @rate_limit(max_calls=30, time_window=60)  # 30 requests per minute
    async def get_events(
        self,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 50,
        calendar_id: str = 'primary'
    ) -> List[Dict[str, Any]]:
        """
        Get calendar events with caching and rate limiting

        Args:
            time_min: Start time (default: now)
            time_max: End time (default: 30 days from now)
            max_results: Maximum number of events
            calendar_id: Calendar ID (default: primary)

        Returns:
            List of calendar events
        """
        start_time = datetime.now()

        try:
            # Default time range if not provided
            if time_min is None:
                time_min = datetime.now()
            if time_max is None:
                time_max = time_min + timedelta(days=30)

            # Call parent method
            events = await super().get_events(
                time_min=time_min,
                time_max=time_max,
                max_results=max_results,
                calendar_id=calendar_id
            )

            # Update health metrics
            elapsed = (datetime.now() - start_time).total_seconds()
            self._update_health_metrics(success=True, response_time=elapsed)

            self.health_status["last_sync"] = datetime.now()
            return events

        except Exception as e:
            logger.error(f"Failed to get calendar events: {e}")
            self._update_health_metrics(success=False)
            raise

    async def batch_create_events(
        self,
        events: List[Dict[str, Any]],
        calendar_id: str = 'primary'
    ) -> Dict[str, Any]:
        """
        Create multiple events in batch

        Args:
            events: List of event dictionaries
            calendar_id: Calendar ID

        Returns:
            Summary of created events
        """
        results = {
            "created": 0,
            "failed": 0,
            "errors": []
        }

        # Create events concurrently (with rate limiting)
        tasks = []
        for event_data in events:
            task = self.create_event(
                summary=event_data.get("summary", ""),
                start_time=event_data.get("start_time"),
                end_time=event_data.get("end_time"),
                description=event_data.get("description", ""),
                location=event_data.get("location", ""),
                calendar_id=calendar_id
            )
            tasks.append(task)

        # Execute with controlled concurrency
        for i in range(0, len(tasks), 5):  # Batch of 5
            batch = tasks[i:i+5]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    results["failed"] += 1
                    results["errors"].append(str(result))
                else:
                    results["created"] += 1

            # Small delay between batches
            if i + 5 < len(tasks):
                await asyncio.sleep(0.5)

        logger.info(f"Batch create: {results['created']} created, {results['failed']} failed")
        return results

    async def get_free_busy(
        self,
        time_min: datetime,
        time_max: datetime,
        calendar_ids: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Get free/busy information for calendars

        Args:
            time_min: Start time
            time_max: End time
            calendar_ids: List of calendar IDs (default: ['primary'])

        Returns:
            Dictionary mapping calendar IDs to busy time slots
        """
        if calendar_ids is None:
            calendar_ids = ['primary']

        try:
            if not self.service:
                await self.authenticate()

            # Build request body
            body = {
                "timeMin": time_min.isoformat() + 'Z',
                "timeMax": time_max.isoformat() + 'Z',
                "items": [{"id": cal_id} for cal_id in calendar_ids]
            }

            # Make API call
            result = self.service.freebusy().query(body=body).execute()

            # Parse calendars
            calendars = result.get('calendars', {})
            busy_times = {}

            for cal_id, cal_data in calendars.items():
                busy_times[cal_id] = cal_data.get('busy', [])

            return busy_times

        except Exception as e:
            logger.error(f"Failed to get free/busy: {e}")
            return {}

    async def find_available_slots(
        self,
        date: datetime,
        duration_minutes: int = 60,
        working_hours: tuple = (9, 17),
        calendar_id: str = 'primary'
    ) -> List[Dict[str, datetime]]:
        """
        Find available time slots on a given day

        Args:
            date: Date to check
            duration_minutes: Duration of slot needed
            working_hours: Tuple of (start_hour, end_hour)
            calendar_id: Calendar ID

        Returns:
            List of available slots with start and end times
        """
        # Get day boundaries
        day_start = date.replace(hour=working_hours[0], minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=working_hours[1], minute=0, second=0, microsecond=0)

        # Get busy times
        busy_times_dict = await self.get_free_busy(day_start, day_end, [calendar_id])
        busy_times = busy_times_dict.get(calendar_id, [])

        # Convert busy times to datetime objects
        busy_slots = []
        for busy in busy_times:
            start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
            busy_slots.append((start, end))

        # Find free slots
        free_slots = []
        current_time = day_start

        while current_time + timedelta(minutes=duration_minutes) <= day_end:
            slot_end = current_time + timedelta(minutes=duration_minutes)

            # Check if this slot overlaps with any busy time
            is_free = True
            for busy_start, busy_end in busy_slots:
                if not (slot_end <= busy_start or current_time >= busy_end):
                    is_free = False
                    current_time = busy_end  # Jump to end of busy period
                    break

            if is_free:
                free_slots.append({
                    "start": current_time,
                    "end": slot_end
                })
                current_time += timedelta(minutes=15)  # Move by 15 min intervals
            else:
                continue

        return free_slots

    async def smart_schedule_event(
        self,
        summary: str,
        duration_minutes: int,
        preferred_days: List[datetime],
        description: str = "",
        location: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Intelligently schedule event in first available slot

        Args:
            summary: Event title
            duration_minutes: Event duration
            preferred_days: List of preferred dates (in order)
            description: Event description
            location: Event location

        Returns:
            Created event or None if no slots available
        """
        for day in preferred_days:
            # Find available slots
            slots = await self.find_available_slots(day, duration_minutes)

            if slots:
                # Take first available slot
                first_slot = slots[0]

                # Create event
                event = await self.create_event(
                    summary=summary,
                    start_time=first_slot["start"],
                    end_time=first_slot["end"],
                    description=description,
                    location=location
                )

                if event:
                    logger.info(f"Smart scheduled: {summary} at {first_slot['start']}")
                    return event

        logger.warning(f"Could not find available slot for: {summary}")
        return None

    def _update_health_metrics(self, success: bool, response_time: float = 0.0):
        """Update service health metrics"""
        self.health_status["total_requests"] += 1

        if not success:
            self.health_status["failed_requests"] += 1

        if response_time > 0:
            # Moving average of response time
            current_avg = self.health_status["average_response_time"]
            total = self.health_status["total_requests"]
            new_avg = ((current_avg * (total - 1)) + response_time) / total
            self.health_status["average_response_time"] = new_avg

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get service health status

        Returns:
            Health status dictionary
        """
        success_rate = 0.0
        if self.health_status["total_requests"] > 0:
            success_rate = (
                (self.health_status["total_requests"] - self.health_status["failed_requests"])
                / self.health_status["total_requests"]
            ) * 100

        return {
            **self.health_status,
            "success_rate": f"{success_rate:.2f}%",
            "is_healthy": success_rate > 90.0 and self.health_status["failed_requests"] < 10,
            "last_sync_ago": (
                str(datetime.now() - self.health_status["last_sync"])
                if self.health_status["last_sync"]
                else "Never"
            )
        }

    async def sync_with_external_calendar(
        self,
        external_events: List[Dict[str, Any]],
        conflict_strategy: str = "skip"
    ) -> Dict[str, Any]:
        """
        Sync events from external source (e.g., Outlook, iCal)

        Args:
            external_events: List of events from external calendar
            conflict_strategy: How to handle conflicts ('skip', 'merge', 'overwrite')

        Returns:
            Sync summary
        """
        results = {
            "synced": 0,
            "skipped": 0,
            "conflicts": 0
        }

        # Get existing events
        existing_events = await self.get_events(
            time_min=datetime.now(),
            time_max=datetime.now() + timedelta(days=90)
        )

        # Build conflict map
        existing_map = {
            (e.get('summary'), e.get('start', {}).get('dateTime')): e
            for e in existing_events
        }

        for ext_event in external_events:
            key = (ext_event.get('summary'), ext_event.get('start_time'))

            if key in existing_map:
                results["conflicts"] += 1
                if conflict_strategy == "skip":
                    results["skipped"] += 1
                    continue

            # Create event
            try:
                await self.create_event(
                    summary=ext_event.get('summary', ''),
                    start_time=ext_event.get('start_time'),
                    end_time=ext_event.get('end_time'),
                    description=ext_event.get('description', ''),
                    location=ext_event.get('location', '')
                )
                results["synced"] += 1
            except Exception as e:
                logger.error(f"Failed to sync event: {e}")
                results["skipped"] += 1

        logger.info(f"Calendar sync: {results['synced']} synced, {results['skipped']} skipped, {results['conflicts']} conflicts")
        return results
