"""Reminders router — CRUD over reminder_service."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.reminder import ReminderCreate, ReminderOut, ReminderUpdate
from app.services import reminder_service

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderOut])
async def list_reminders(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    return await reminder_service.list_reminders(db, user.id)


@router.post("", response_model=ReminderOut, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    payload: ReminderCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await reminder_service.create_reminder(db, user.id, payload)


@router.patch("/{reminder_id}", response_model=ReminderOut)
async def update_reminder(
    reminder_id: int,
    payload: ReminderUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await reminder_service.update_reminder(db, user.id, reminder_id, payload)


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await reminder_service.delete_reminder(db, user.id, reminder_id)
