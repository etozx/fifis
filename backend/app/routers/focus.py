"""
Focus block router — the timer's command surface.

Routes (all under /api/v1):
  POST /focus/start
  POST /focus/{block_id}/pause
  POST /focus/{block_id}/resume
  POST /focus/{block_id}/complete
  GET  /focus/history
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.focus_block import FocusBlock
from app.models.user import User
from app.schemas.focus import FocusBlockOut, FocusComplete, FocusStart
from app.services import focus_service

router = APIRouter(prefix="/focus", tags=["focus"])


def _to_out(block: FocusBlock) -> FocusBlockOut:
    """Attach the server-computed live elapsed time to the response model."""
    return FocusBlockOut(
        id=block.id,
        goal_id=block.goal_id,
        status=block.status,
        started_at=block.started_at,
        ended_at=block.ended_at,
        accumulated_seconds=block.accumulated_seconds,
        notes=block.notes,
        elapsed_seconds=focus_service.compute_elapsed_seconds(block),
    )


@router.post("/start", response_model=FocusBlockOut, status_code=status.HTTP_201_CREATED)
async def start_focus(
    payload: FocusStart,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    block = await focus_service.start_block(db, user.id, payload.goal_id, payload.notes)
    return _to_out(block)


@router.post("/{block_id}/pause", response_model=FocusBlockOut)
async def pause_focus(
    block_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    block = await focus_service.pause_block(db, user.id, block_id)
    return _to_out(block)


@router.post("/{block_id}/resume", response_model=FocusBlockOut)
async def resume_focus(
    block_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    block = await focus_service.resume_block(db, user.id, block_id)
    return _to_out(block)


@router.post("/{block_id}/complete", response_model=FocusBlockOut)
async def complete_focus(
    block_id: int,
    payload: FocusComplete,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    block = await focus_service.complete_block(db, user.id, block_id, payload.notes)
    return _to_out(block)


@router.get("/history", response_model=list[FocusBlockOut])
async def focus_history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    blocks = await focus_service.list_history(db, user.id)
    return [_to_out(b) for b in blocks]
