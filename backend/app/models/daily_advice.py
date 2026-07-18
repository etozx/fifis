"""
DailyAdvice model — seeded catalog of short motivational/practical advice.

Rule-based now (a weighted catalog), but the schema (category/tags/weight) is
shaped so an AI generator can later insert or rank rows without changing the
read path.
"""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.types import JSONList


class DailyAdvice(Base):
    __tablename__ = "daily_advice"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="general", nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONList, default=list)
    # Higher weight -> more likely to be surfaced by the picker.
    weight: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
