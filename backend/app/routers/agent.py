"""
AI Focus Agent router.

Gathers the `AgentContext` from the datastore and delegates the actual decision
to whatever `FocusAgent` implementation `get_focus_agent()` returns.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.task import Task
from app.models.user import User
from app.schemas.agent import AgentRecommendation
from app.services import focus_service, goal_service
from app.services.focus_agent import AgentContext, get_focus_agent

router = APIRouter(prefix="/agent", tags=["agent"])


@router.get("/recommendation", response_model=AgentRecommendation)
async def recommendation(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the agent's suggested next goal, focus duration, and nudge."""
    goals = await goal_service.list_goals(db, user.id)
    goal_ids = [g.id for g in goals]

    tasks_by_goal: dict[int, list[Task]] = {gid: [] for gid in goal_ids}
    if goal_ids:
        task_rows = await db.scalars(select(Task).where(Task.goal_id.in_(goal_ids)))
        for task in task_rows:
            tasks_by_goal.setdefault(task.goal_id, []).append(task)

    recent_blocks = await focus_service.list_history(db, user.id, limit=50)

    context = AgentContext(
        now=datetime.now(timezone.utc),
        goals=goals,
        tasks_by_goal=tasks_by_goal,
        recent_blocks=recent_blocks,
    )
    return get_focus_agent().recommend(context)
