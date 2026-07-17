"""
FocusBlock model — a single focus session with pause/resume support.

The elapsed time is computed server-side, not trusted from the client clock.
`accumulated_seconds` banks time from every completed run interval; when a block
is actively running, `last_resumed_at` marks the start of the current interval so
live elapsed = accumulated_seconds + (now - last_resumed_at).
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FocusStatus(str, enum.Enum):
    active = "active"      # currently running
    paused = "paused"      # started but paused
    completed = "completed"  # finished normally
    abandoned = "abandoned"  # cancelled without completing


class FocusBlock(Base):
    __tablename__ = "focus_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    goal_id: Mapped[int | None] = mapped_column(
        ForeignKey("goals.id", ondelete="SET NULL"), index=True, nullable=True
    )
    status: Mapped[FocusStatus] = mapped_column(
        Enum(FocusStatus), default=FocusStatus.active, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_resumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accumulated_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="focus_blocks")  # noqa: F821
