"""
AI Focus Agent.

Design intent (System Design Primer — clear service boundary): the agent is a
self-contained module behind a single abstract interface, `FocusAgent`. The rest
of the app depends only on `FocusAgent.recommend(...)`, never on how the
recommendation is produced.

Today the concrete implementation is `RuleBasedFocusAgent` — transparent,
deterministic heuristics with zero external dependencies. Tomorrow an
`LLMFocusAgent` can implement the same interface (calling an LLM with the same
`AgentContext`) and be swapped in via `get_focus_agent()` with no changes to the
router, schema, or frontend.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from app.models.focus_block import FocusBlock, FocusStatus
from app.models.goal import Goal, GoalStatus
from app.models.task import Task, TaskStatus
from app.schemas.agent import AgentRecommendation

# Focus-duration guardrails (minutes). Kept as named constants so the heuristic
# reads declaratively (ECC: intention-revealing values, not magic numbers).
DEFAULT_FOCUS_MINUTES = 25  # a classic pomodoro when we have no history
MIN_FOCUS_MINUTES = 15
MAX_FOCUS_MINUTES = 50


@dataclass
class AgentContext:
    """Everything the agent needs to reason, gathered by the router."""

    now: datetime
    goals: list[Goal]
    tasks_by_goal: dict[int, list[Task]] = field(default_factory=dict)
    recent_blocks: list[FocusBlock] = field(default_factory=list)


class FocusAgent(ABC):
    """Abstract focus agent. Implementations must be pure w.r.t. `AgentContext`."""

    @abstractmethod
    def recommend(self, context: AgentContext) -> AgentRecommendation:
        """Return a next-action recommendation for the user."""
        raise NotImplementedError


class RuleBasedFocusAgent(FocusAgent):
    """
    Transparent heuristic agent.

    Scoring picks the single goal most worth attention right now by combining:
      - urgency: how close the target date is (closer -> higher);
      - staleness: how long since the goal last received focus;
      - momentum gap: number of still-open tasks.
    It then suggests a focus duration adapted from the user's recent completed
    sessions, and emits a short contextual nudge.
    """

    def recommend(self, context: AgentContext) -> AgentRecommendation:
        active_goals = [g for g in context.goals if g.status == GoalStatus.active]

        if not active_goals:
            return AgentRecommendation(
                suggested_goal_id=None,
                suggested_goal_title=None,
                suggested_focus_minutes=DEFAULT_FOCUS_MINUTES,
                nudge="No active goals yet — set one meaningful goal to aim at today.",
                rationale="There are no active goals to prioritize.",
            )

        last_focus_by_goal = self._last_focus_by_goal(context.recent_blocks)
        today = context.now.date()

        scored = [
            (self._score_goal(goal, context, last_focus_by_goal, today), goal)
            for goal in active_goals
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        best_score, best_goal = scored[0]

        minutes = self._suggested_minutes(context.recent_blocks)
        open_tasks = self._open_task_count(best_goal.id, context)
        nudge = self._build_nudge(best_goal, open_tasks, minutes, today)

        return AgentRecommendation(
            suggested_goal_id=best_goal.id,
            suggested_goal_title=best_goal.title,
            suggested_focus_minutes=minutes,
            nudge=nudge,
            rationale=(
                f"Selected '{best_goal.title}' (priority score {best_score:.1f}) "
                f"from {len(active_goals)} active goals based on deadline urgency, "
                f"time since last focus, and {open_tasks} open task(s)."
            ),
        )

    # --- heuristics --------------------------------------------------------
    @staticmethod
    def _last_focus_by_goal(blocks: list[FocusBlock]) -> dict[int, datetime]:
        last: dict[int, datetime] = {}
        for block in blocks:
            if block.goal_id is None:
                continue
            started = _as_aware(block.started_at)
            if block.goal_id not in last or started > last[block.goal_id]:
                last[block.goal_id] = started
        return last

    def _score_goal(
        self,
        goal: Goal,
        context: AgentContext,
        last_focus_by_goal: dict[int, datetime],
        today: date,
    ) -> float:
        score = 0.0

        # Urgency: the closer (or more overdue) the target date, the higher.
        if goal.target_date is not None:
            days_left = (goal.target_date - today).days
            if days_left <= 0:
                score += 40  # overdue — strong pull
            elif days_left <= 3:
                score += 30
            elif days_left <= 7:
                score += 20
            elif days_left <= 30:
                score += 10

        # Staleness: reward goals that haven't been touched recently.
        last = last_focus_by_goal.get(goal.id)
        if last is None:
            score += 15  # never focused
        else:
            days_since = (context.now - last).days
            score += min(days_since * 2, 20)

        # Momentum gap: open tasks mean there's concrete work to do.
        score += min(self._open_task_count(goal.id, context) * 3, 15)
        return score

    @staticmethod
    def _open_task_count(goal_id: int, context: AgentContext) -> int:
        tasks = context.tasks_by_goal.get(goal_id, [])
        return sum(1 for t in tasks if t.status != TaskStatus.done)

    @staticmethod
    def _suggested_minutes(blocks: list[FocusBlock]) -> int:
        """Adapt duration to the user's recent completed sessions."""
        completed = [
            b.accumulated_seconds
            for b in blocks
            if b.status == FocusStatus.completed and b.accumulated_seconds > 0
        ]
        if not completed:
            return DEFAULT_FOCUS_MINUTES
        avg_minutes = (sum(completed) / len(completed)) / 60
        # Nudge slightly above their average to build capacity, within guardrails.
        target = round(avg_minutes * 1.1)
        return max(MIN_FOCUS_MINUTES, min(MAX_FOCUS_MINUTES, target))

    @staticmethod
    def _build_nudge(goal: Goal, open_tasks: int, minutes: int, today: date) -> str:
        if goal.target_date is not None:
            days_left = (goal.target_date - today).days
            if days_left < 0:
                timing = f"'{goal.title}' is past its target date"
            elif days_left == 0:
                timing = f"'{goal.title}' is due today"
            else:
                timing = f"'{goal.title}' has {days_left} day(s) left"
        else:
            timing = f"'{goal.title}' is waiting for progress"

        if open_tasks > 0:
            return (
                f"{timing}. Start a {minutes}-minute focus block and clear one of "
                f"its {open_tasks} open task(s)."
            )
        return f"{timing}. A {minutes}-minute focus block will keep the momentum going."


def get_focus_agent() -> FocusAgent:
    """
    Factory for the active focus agent.

    Swap the return value here (e.g. for an `LLMFocusAgent`) to change the
    strategy app-wide without touching callers.
    """
    return RuleBasedFocusAgent()


def _as_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
