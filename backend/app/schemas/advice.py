"""Daily advice schemas."""

from pydantic import BaseModel, ConfigDict


class AdviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    category: str
    tags: list[str]
