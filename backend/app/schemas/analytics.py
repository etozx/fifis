"""Analytics dashboard schemas."""

from pydantic import BaseModel


class TimePoint(BaseModel):
    """Focus minutes on a given calendar day (ISO date string)."""

    date: str
    minutes: int


class CategorySlice(BaseModel):
    """Total focus minutes attributed to a goal category."""

    category: str
    minutes: int


class AnalyticsSummary(BaseModel):
    """
    The personal-growth-intelligence payload backing the dashboard.

    Framed as insight, not raw logs: totals, momentum (streaks), and where the
    user's attention actually went (category distribution).
    """

    range_days: int
    total_focus_minutes: int
    focus_by_day: list[TimePoint]
    completed_tasks: int
    active_goals: int
    current_streak_days: int
    longest_streak_days: int
    category_distribution: list[CategorySlice]
