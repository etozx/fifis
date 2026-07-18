"""
Goals & nested tasks router — thin HTTP layer over goal_service.

Routes (all under /api/v1):
  GET    /goals
  POST   /goals
  GET    /goals/{goal_id}
  PATCH  /goals/{goal_id}
  DELETE /goals/{goal_id}
  POST   /goals/{goal_id}/tasks
  PATCH  /goals/{goal_id}/tasks/{task_id}
  DELETE /goals/{goal_id}/tasks/{task_id}
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.goal import (
    GoalCreate,
    GoalDetailOut,
    GoalOut,
    GoalUpdate,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)
from app.services import goal_service

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("", response_model=list[GoalOut])
async def list_goals(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    return await goal_service.list_goals(db, user.id)


@router.post("", response_model=GoalDetailOut, status_code=status.HTTP_201_CREATED)
async def create_goal(
    payload: GoalCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await goal_service.create_goal(db, user.id, payload)


@router.get("/{goal_id}", response_model=GoalDetailOut)
async def get_goal(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await goal_service.get_goal(db, user.id, goal_id)


@router.patch("/{goal_id}", response_model=GoalDetailOut)
async def update_goal(
    goal_id: int,
    payload: GoalUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await goal_service.update_goal(db, user.id, goal_id, payload)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await goal_service.delete_goal(db, user.id, goal_id)


# --- Nested tasks ----------------------------------------------------------
@router.post(
    "/{goal_id}/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED
)
async def add_task(
    goal_id: int,
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await goal_service.add_task(db, user.id, goal_id, payload)


@router.patch("/{goal_id}/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    goal_id: int,
    task_id: int,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await goal_service.update_task(db, user.id, goal_id, task_id, payload)


@router.delete(
    "/{goal_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_task(
    goal_id: int,
    task_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await goal_service.delete_task(db, user.id, goal_id, task_id)
