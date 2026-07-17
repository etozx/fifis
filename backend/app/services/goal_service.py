"""
Goal & Task business logic.

Every read/write is scoped to the owning user, so ownership checks live in one
place rather than being re-derived in each router.
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.goal import Goal, GoalStatus
from app.models.task import Task, TaskStatus
from app.schemas.goal import GoalCreate, GoalUpdate, TaskCreate, TaskUpdate


# --- Goals -----------------------------------------------------------------
async def list_goals(db: AsyncSession, user_id: int) -> list[Goal]:
    result = await db.scalars(
        select(Goal).where(Goal.user_id == user_id).order_by(Goal.created_at.desc())
    )
    return list(result)


async def get_goal(db: AsyncSession, user_id: int, goal_id: int) -> Goal:
    """Fetch a goal (with tasks eagerly loaded) or raise 404 if not owned."""
    goal = await db.scalar(
        select(Goal)
        .where(Goal.id == goal_id, Goal.user_id == user_id)
        .options(selectinload(Goal.tasks))
    )
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal


async def create_goal(db: AsyncSession, user_id: int, payload: GoalCreate) -> Goal:
    goal = Goal(user_id=user_id, **payload.model_dump())
    db.add(goal)
    await db.commit()
    await db.refresh(goal, attribute_names=["tasks"])
    return goal


async def update_goal(
    db: AsyncSession, user_id: int, goal_id: int, payload: GoalUpdate
) -> Goal:
    goal = await get_goal(db, user_id, goal_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)
    await db.commit()
    await db.refresh(goal, attribute_names=["tasks"])
    return goal


async def delete_goal(db: AsyncSession, user_id: int, goal_id: int) -> None:
    goal = await get_goal(db, user_id, goal_id)
    await db.delete(goal)
    await db.commit()


# --- Tasks -----------------------------------------------------------------
async def add_task(
    db: AsyncSession, user_id: int, goal_id: int, payload: TaskCreate
) -> Task:
    # get_goal enforces ownership before we attach a task.
    await get_goal(db, user_id, goal_id)
    task = Task(goal_id=goal_id, **payload.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def update_task(
    db: AsyncSession, user_id: int, goal_id: int, task_id: int, payload: TaskUpdate
) -> Task:
    await get_goal(db, user_id, goal_id)
    task = await db.scalar(
        select(Task).where(Task.id == task_id, Task.goal_id == goal_id)
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    data = payload.model_dump(exclude_unset=True)
    # Stamp completion time when a task transitions to/from done.
    if "status" in data:
        if data["status"] == TaskStatus.done and task.completed_at is None:
            task.completed_at = datetime.now(timezone.utc)
        elif data["status"] != TaskStatus.done:
            task.completed_at = None
    for field, value in data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(
    db: AsyncSession, user_id: int, goal_id: int, task_id: int
) -> None:
    await get_goal(db, user_id, goal_id)
    task = await db.scalar(
        select(Task).where(Task.id == task_id, Task.goal_id == goal_id)
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    await db.delete(task)
    await db.commit()


async def count_active_goals(db: AsyncSession, user_id: int) -> int:
    goals = await list_goals(db, user_id)
    return sum(1 for g in goals if g.status == GoalStatus.active)
