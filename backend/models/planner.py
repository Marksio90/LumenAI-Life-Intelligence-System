"""
Planner Models - Task and Calendar Event Management
Defines schemas for tasks and calendar events
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """Task status enum"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskPriority(str, Enum):
    """Task priority enum"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskBase(BaseModel):
    """Base task schema"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    category: Optional[str] = None


class TaskCreate(TaskBase):
    """Schema for creating a task"""
    pass


class TaskUpdate(BaseModel):
    """Schema for updating a task"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[datetime] = None
    category: Optional[str] = None


class TaskInDB(TaskBase):
    """Task schema stored in database"""
    task_id: str
    user_id: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_123abc",
                "user_id": "user_123",
                "title": "Complete project report",
                "description": "Finish the quarterly report",
                "priority": "high",
                "status": "in_progress",
                "due_date": "2025-12-10T17:00:00",
                "category": "work",
                "created_at": "2025-12-05T10:00:00",
            }
        }


class TaskPublic(TaskBase):
    """Public task schema"""
    task_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class CalendarEventBase(BaseModel):
    """Base calendar event schema"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    color: Optional[str] = None


class CalendarEventCreate(CalendarEventBase):
    """Schema for creating a calendar event"""
    pass


class CalendarEventInDB(CalendarEventBase):
    """Calendar event schema stored in database"""
    event_id: str
    user_id: str
    google_event_id: Optional[str] = None  # If synced with Google Calendar
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "event_123abc",
                "user_id": "user_123",
                "title": "Team Meeting",
                "description": "Weekly team sync",
                "start_time": "2025-12-06T10:00:00",
                "end_time": "2025-12-06T11:00:00",
                "location": "Conference Room A",
                "created_at": "2025-12-05T10:00:00",
            }
        }


class CalendarEventPublic(CalendarEventBase):
    """Public calendar event schema"""
    event_id: str
    created_at: datetime
