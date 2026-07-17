"""AI Focus Agent schemas."""

from pydantic import BaseModel


class AgentRecommendation(BaseModel):
    """
    A recommendation from the focus agent.

    This is the stable contract between the agent implementation and the API. A
    future LLM-backed agent must return this same shape, so the router and
    frontend never need to change.
    """

    suggested_goal_id: int | None
    suggested_goal_title: str | None
    suggested_focus_minutes: int
    nudge: str
    rationale: str
