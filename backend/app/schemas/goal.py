"""Goal & Task schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.goal import GoalStatus
from app.models.task import TaskStatus


# --- Tasks -----------------------------------------------------------------
class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    due_date: date | None = None
    position: int = 0


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None
    status: TaskStatus | None = None
    due_date: date | None = None
    position: int | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    goal_id: int
    title: str
    description: str | None
    status: TaskStatus
    due_date: date | None
    position: int
    completed_at: datetime | None


# --- Goals -----------------------------------------------------------------
class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category: str = Field(default="general", max_length=60)
    target_date: date | None = None
    tags: list[str] = Field(default_factory=list)


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None
    category: str | None = Field(default=None, max_length=60)
    target_date: date | None = None
    status: GoalStatus | None = None
    tags: list[str] | None = None


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    category: str
    target_date: date | None
    status: GoalStatus
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class GoalDetailOut(GoalOut):
    tasks: list[TaskOut] = Field(default_factory=list)
