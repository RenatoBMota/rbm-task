from datetime import datetime
from pydantic import BaseModel


class PrioritySuggestion(BaseModel):
    task_id: int
    title: str
    score: int
    reason: str


class TimeEstimate(BaseModel):
    estimated_minutes: int | None
    sample_size: int


class RiskTask(BaseModel):
    task_id: int
    title: str
    risk: str
    deadline: datetime
