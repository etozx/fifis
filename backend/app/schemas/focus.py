"""Focus block schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.focus_block import FocusStatus


class FocusStart(BaseModel):
    goal_id: int | None = None
    notes: str | None = None


class FocusComplete(BaseModel):
    notes: str | None = None


class FocusBlockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    goal_id: int | None
    status: FocusStatus
    started_at: datetime
    ended_at: datetime | None
    accumulated_seconds: int
    notes: str | None
    # Live elapsed seconds (banked + current running interval), computed server-side.
    elapsed_seconds: int
