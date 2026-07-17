"""
Analytics aggregation for the personal-growth dashboard.

System Design Primer pattern applied: this is a read-heavy endpoint hit on every
dashboard load, so results are cached in Redis keyed by (user, range). The cache
is invalidated implicitly by a short TTL — acceptable because the numbers are
insight, not transactional.
"""

import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.focus_block import FocusBlock, FocusStatus
from app.models.goal import Goal, GoalStatus
from app.models.task import Task, TaskStatus

_CACHE_TTL_SECONDS = 120


def _as_utc_date(dt: datetime) -> date:
    aware = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).date()


def _streaks(focus_days: set[date], today: date) -> tuple[int, int]:
    """
    Compute (current_streak, longest_streak) in days from the set of days that
    had at least one completed focus block.
    """
    if not focus_days:
        return 0, 0

    # Longest run of consecutive days anywhere in the set.
    ordered = sorted(focus_days)
    longest = run = 1
    for prev, cur in zip(ordered, ordered[1:]):
        run = run + 1 if (cur - prev).days == 1 else 1
        longest = max(longest, run)

    # Current streak counts back from today (or yesterday, if today is empty yet).
    current = 0
    cursor = today if today in focus_days else today - timedelta(days=1)
    while cursor in focus_days:
        current += 1
        cursor -= timedelta(days=1)

    return current, longest


async def get_summary(
    db: AsyncSession, redis: Redis, user_id: int, range_days: int = 30
) -> dict:
    """Aggregate focus time, completed tasks, streaks, and category split."""
    cache_key = f"analytics:{user_id}:{range_days}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    today = datetime.now(timezone.utc).date()
    window_start = today - timedelta(days=range_days - 1)

    # Completed focus blocks in-window drive both the time series and streaks.
    blocks = list(
        await db.scalars(
            select(FocusBlock).where(
                FocusBlock.user_id == user_id,
                FocusBlock.status == FocusStatus.completed,
            )
        )
    )

    minutes_by_day: dict[str, int] = defaultdict(int)
    focus_days: set[date] = set()
    goal_ids_seen: set[int] = set()
    minutes_by_goal: dict[int | None, int] = defaultdict(int)

    for block in blocks:
        block_day = _as_utc_date(block.started_at)
        focus_days.add(block_day)
        minutes = block.accumulated_seconds // 60
        if block_day >= window_start:
            minutes_by_day[block_day.isoformat()] += minutes
            minutes_by_goal[block.goal_id] += minutes
            if block.goal_id is not None:
                goal_ids_seen.add(block.goal_id)

    # Dense day series (zero-filled) so the chart has no gaps.
    focus_by_day = [
        {
            "date": (window_start + timedelta(days=offset)).isoformat(),
            "minutes": minutes_by_day.get(
                (window_start + timedelta(days=offset)).isoformat(), 0
            ),
        }
        for offset in range(range_days)
    ]

    current_streak, longest_streak = _streaks(focus_days, today)

    # Map goal -> category for the distribution chart.
    goals = list(await db.scalars(select(Goal).where(Goal.user_id == user_id)))
    category_by_goal = {g.id: g.category for g in goals}
    active_goals = sum(1 for g in goals if g.status == GoalStatus.active)

    minutes_by_category: dict[str, int] = defaultdict(int)
    for goal_id, minutes in minutes_by_goal.items():
        category = category_by_goal.get(goal_id, "unassigned")
        minutes_by_category[category] += minutes
    category_distribution = [
        {"category": category, "minutes": minutes}
        for category, minutes in sorted(
            minutes_by_category.items(), key=lambda kv: kv[1], reverse=True
        )
    ]

    # Completed tasks in-window.
    completed_task_rows = list(
        await db.scalars(
            select(Task)
            .join(Goal, Task.goal_id == Goal.id)
            .where(Goal.user_id == user_id, Task.status == TaskStatus.done)
        )
    )
    completed_tasks = sum(
        1
        for t in completed_task_rows
        if t.completed_at is None or _as_utc_date(t.completed_at) >= window_start
    )

    summary = {
        "range_days": range_days,
        "total_focus_minutes": sum(p["minutes"] for p in focus_by_day),
        "focus_by_day": focus_by_day,
        "completed_tasks": completed_tasks,
        "active_goals": active_goals,
        "current_streak_days": current_streak,
        "longest_streak_days": longest_streak,
        "category_distribution": category_distribution,
    }

    await redis.set(cache_key, json.dumps(summary), ex=_CACHE_TTL_SECONDS)
    return summary
