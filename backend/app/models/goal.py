"""Goal model — the top-level unit a user is working toward."""

import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.types import JSONList


class GoalStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    paused = "paused"
    archived = "archived"


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(60), default="general", nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus), default=GoalStatus.active, nullable=False
    )
    # Portable JSON list of string tags (see app/models/types.py).
    tags: Mapped[list[str]] = mapped_column(JSONList, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="goals")  # noqa: F821
    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        back_populates="goal", cascade="all, delete-orphan", order_by="Task.position"
    )
