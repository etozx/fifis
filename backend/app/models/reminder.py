"""
Reminder model.

Scope note (from the plan): reminders are full CRUD with `next_run_at`
computed on write. Actually *firing* reminders (push/email) is a separate
worker/Render-Cron concern and is intentionally left as a marked extension
point — see app/services/... and the README.
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.types import JSONList


class ScheduleType(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    custom = "custom"


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    goal_id: Mapped[int | None] = mapped_column(
        ForeignKey("goals.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    schedule_type: Mapped[ScheduleType] = mapped_column(
        Enum(ScheduleType), default=ScheduleType.daily, nullable=False
    )
    # Flexible config: {"time": "09:00", "days": ["mon","wed"], "cron": "..."}
    schedule_config: Mapped[list] = mapped_column(JSONList, default=list)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="reminders")  # noqa: F821
