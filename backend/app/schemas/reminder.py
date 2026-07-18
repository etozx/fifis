"""Reminder schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.reminder import ScheduleType


class ReminderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    goal_id: int | None = None
    schedule_type: ScheduleType = ScheduleType.daily
    # e.g. {"time": "09:00", "days": ["mon", "wed"]}
    schedule_config: dict = Field(default_factory=dict)


class ReminderUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    schedule_type: ScheduleType | None = None
    schedule_config: dict | None = None
    is_active: bool | None = None


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    goal_id: int | None
    schedule_type: ScheduleType
    schedule_config: dict | list
    next_run_at: datetime | None
    is_active: bool
