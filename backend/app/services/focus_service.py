"""
Focus block business logic.

The server is the single source of truth for elapsed time. Clients only issue
start / pause / resume / complete commands; the accumulated duration is derived
from server timestamps so a user can't inflate their focus stats by tampering
with a client-side timer.
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.focus_block import FocusBlock, FocusStatus


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime | None) -> datetime | None:
    """Treat naive timestamps (sqlite) as UTC so arithmetic stays correct."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def compute_elapsed_seconds(block: FocusBlock) -> int:
    """Banked seconds plus the current running interval (if active)."""
    elapsed = block.accumulated_seconds
    if block.status == FocusStatus.active and block.last_resumed_at is not None:
        elapsed += int((_now() - _as_aware(block.last_resumed_at)).total_seconds())
    return max(elapsed, 0)


async def _get_owned_block(db: AsyncSession, user_id: int, block_id: int) -> FocusBlock:
    block = await db.scalar(
        select(FocusBlock).where(
            FocusBlock.id == block_id, FocusBlock.user_id == user_id
        )
    )
    if block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Focus block not found"
        )
    return block


async def start_block(
    db: AsyncSession, user_id: int, goal_id: int | None, notes: str | None
) -> FocusBlock:
    """Start a new focus block in the active/running state."""
    now = _now()
    block = FocusBlock(
        user_id=user_id,
        goal_id=goal_id,
        status=FocusStatus.active,
        started_at=now,
        last_resumed_at=now,
        accumulated_seconds=0,
        notes=notes,
    )
    db.add(block)
    await db.commit()
    await db.refresh(block)
    return block


async def pause_block(db: AsyncSession, user_id: int, block_id: int) -> FocusBlock:
    """Bank the current interval and move the block to paused."""
    block = await _get_owned_block(db, user_id, block_id)
    if block.status != FocusStatus.active:
        raise HTTPException(status_code=409, detail="Focus block is not running")

    block.accumulated_seconds = compute_elapsed_seconds(block)
    block.last_resumed_at = None
    block.status = FocusStatus.paused
    await db.commit()
    await db.refresh(block)
    return block


async def resume_block(db: AsyncSession, user_id: int, block_id: int) -> FocusBlock:
    """Resume a paused block, starting a new running interval."""
    block = await _get_owned_block(db, user_id, block_id)
    if block.status != FocusStatus.paused:
        raise HTTPException(status_code=409, detail="Focus block is not paused")

    block.last_resumed_at = _now()
    block.status = FocusStatus.active
    await db.commit()
    await db.refresh(block)
    return block


async def complete_block(
    db: AsyncSession, user_id: int, block_id: int, notes: str | None
) -> FocusBlock:
    """Finalize a block, banking any running interval into the total."""
    block = await _get_owned_block(db, user_id, block_id)
    if block.status in (FocusStatus.completed, FocusStatus.abandoned):
        raise HTTPException(status_code=409, detail="Focus block already finished")

    block.accumulated_seconds = compute_elapsed_seconds(block)
    block.last_resumed_at = None
    block.ended_at = _now()
    block.status = FocusStatus.completed
    if notes is not None:
        block.notes = notes
    await db.commit()
    await db.refresh(block)
    return block


async def list_history(
    db: AsyncSession, user_id: int, limit: int = 50
) -> list[FocusBlock]:
    """Return recent focus blocks, newest first."""
    result = await db.scalars(
        select(FocusBlock)
        .where(FocusBlock.user_id == user_id)
        .order_by(FocusBlock.started_at.desc())
        .limit(limit)
    )
    return list(result)
