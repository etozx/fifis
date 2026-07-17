"""
Seed data for the advice catalog.

Idempotent: only inserts when the table is empty, so it is safe to run on every
startup in the scaffold. Content is intentionally short, practical, and
category-tagged so the picker (and a future AI ranker) can filter by theme.
"""

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.daily_advice import DailyAdvice

_SEED_ADVICE: list[dict] = [
    {"text": "Start before you feel ready — momentum follows action, not the other way around.", "category": "motivation", "tags": ["start", "momentum"], "weight": 3},
    {"text": "Pick the smallest next step you can finish in one focus block, then do only that.", "category": "focus", "tags": ["small-steps"], "weight": 3},
    {"text": "Protect one distraction-free block today. Phone in another room, one tab open.", "category": "focus", "tags": ["deep-work"], "weight": 2},
    {"text": "Progress compounds. A 25-minute block every day beats a rare marathon session.", "category": "consistency", "tags": ["streak", "habit"], "weight": 3},
    {"text": "Name the one task that would make today a win. Start there.", "category": "prioritization", "tags": ["priority"], "weight": 2},
    {"text": "Done is a direction, not a destination. Ship the rough version and refine later.", "category": "motivation", "tags": ["shipping"], "weight": 2},
    {"text": "If a task feels too big, it's not one task. Split it until the first step is obvious.", "category": "planning", "tags": ["decompose"], "weight": 2},
    {"text": "Rest is part of the work. Take the break so the next block is sharp.", "category": "wellbeing", "tags": ["rest"], "weight": 1},
    {"text": "Review your goals weekly. What matters changes — your focus should too.", "category": "reflection", "tags": ["review"], "weight": 1},
    {"text": "You don't need motivation to start a 15-minute timer. You just need to start it.", "category": "focus", "tags": ["pomodoro"], "weight": 2},
]


async def seed_advice_if_empty() -> None:
    """Insert the default advice catalog if none exists yet."""
    async with AsyncSessionLocal() as db:
        count = await db.scalar(select(func.count()).select_from(DailyAdvice))
        if count and count > 0:
            return
        db.add_all(DailyAdvice(**row) for row in _SEED_ADVICE)
        await db.commit()
