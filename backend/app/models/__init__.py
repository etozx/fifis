"""ORM models. Importing this package registers every model on Base.metadata."""

from app.models.daily_advice import DailyAdvice
from app.models.focus_block import FocusBlock, FocusStatus
from app.models.goal import Goal, GoalStatus
from app.models.reminder import Reminder, ScheduleType
from app.models.task import Task, TaskStatus
from app.models.user import User

__all__ = [
    "User",
    "Goal",
    "GoalStatus",
    "Task",
    "TaskStatus",
    "FocusBlock",
    "FocusStatus",
    "Reminder",
    "ScheduleType",
    "DailyAdvice",
]
