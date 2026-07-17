"""
Reminder business logic — CRUD plus `next_run_at` computation.

Scope boundary (from the plan): this computes *when* a reminder should next fire
and stores it. It does not *deliver* reminders. Delivery belongs to a separate
scheduled worker (e.g. a Render Cron Job) that polls
`SELECT * FROM reminders WHERE is_active AND next_run_at <= now()`, dispatches the
notification, then advances `next_run_at`. That worker is the marked extension
point and is intentionally not built in this scaffold.
"""

from datetime import datetime, time, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder import Reminder, ScheduleType
from app.schemas.reminder import ReminderCreate, ReminderUpdate

_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _parse_time(config: dict) -> time:
    """Read a 'HH:MM' time from config, defaulting to 09:00."""
    raw = str(config.get("time", "09:00"))
    try:
        hour, minute = (int(part) for part in raw.split(":", 1))
        return time(hour=hour, minute=minute)
    except (ValueError, TypeError):
        return time(hour=9, minute=0)


def compute_next_run(schedule_type: ScheduleType, config: dict) -> datetime | None:
    """
    Compute the next fire time in UTC.

    - daily:  next occurrence of the configured time.
    - weekly: next configured weekday at the configured time.
    - custom: caller may pass an explicit ISO 'next_run_at'; otherwise None
              (a cron-style parser would live here in a fuller build).
    """
    now = datetime.now(timezone.utc)
    target = _parse_time(config)

    if schedule_type == ScheduleType.daily:
        candidate = now.replace(
            hour=target.hour, minute=target.minute, second=0, microsecond=0
        )
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    if schedule_type == ScheduleType.weekly:
        days = [d.lower()[:3] for d in config.get("days", [])]
        wanted = [_WEEKDAYS.index(d) for d in days if d in _WEEKDAYS]
        if not wanted:
            return None
        for offset in range(0, 8):
            candidate = (now + timedelta(days=offset)).replace(
                hour=target.hour, minute=target.minute, second=0, microsecond=0
            )
            if candidate.weekday() in wanted and candidate > now:
                return candidate
        return None

    # custom
    explicit = config.get("next_run_at")
    if explicit:
        try:
            return datetime.fromisoformat(explicit)
        except ValueError:
            return None
    return None


async def list_reminders(db: AsyncSession, user_id: int) -> list[Reminder]:
    result = await db.scalars(
        select(Reminder).where(Reminder.user_id == user_id).order_by(Reminder.id)
    )
    return list(result)


async def create_reminder(
    db: AsyncSession, user_id: int, payload: ReminderCreate
) -> Reminder:
    reminder = Reminder(
        user_id=user_id,
        title=payload.title,
        goal_id=payload.goal_id,
        schedule_type=payload.schedule_type,
        schedule_config=payload.schedule_config,
        next_run_at=compute_next_run(payload.schedule_type, payload.schedule_config),
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder


async def _get_owned(db: AsyncSession, user_id: int, reminder_id: int) -> Reminder:
    reminder = await db.scalar(
        select(Reminder).where(
            Reminder.id == reminder_id, Reminder.user_id == user_id
        )
    )
    if reminder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found"
        )
    return reminder


async def update_reminder(
    db: AsyncSession, user_id: int, reminder_id: int, payload: ReminderUpdate
) -> Reminder:
    reminder = await _get_owned(db, user_id, reminder_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(reminder, field, value)
    # Recompute the next fire time if scheduling changed.
    if "schedule_type" in data or "schedule_config" in data:
        reminder.next_run_at = compute_next_run(
            reminder.schedule_type, reminder.schedule_config or {}
        )
    await db.commit()
    await db.refresh(reminder)
    return reminder


async def delete_reminder(db: AsyncSession, user_id: int, reminder_id: int) -> None:
    reminder = await _get_owned(db, user_id, reminder_id)
    await db.delete(reminder)
    await db.commit()
