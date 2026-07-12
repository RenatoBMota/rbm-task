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


class TeamWorkload(BaseModel):
    user_id: int
    full_name: str
    active_task_count: int
    weighted_load: int
    is_overloaded: bool


class ProjectRisk(BaseModel):
    project_id: int
    total_tasks: int
    overdue: int
    at_risk: int
    breached: int
    risk_score: float
    level: str
