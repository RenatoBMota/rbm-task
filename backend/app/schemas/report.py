from datetime import datetime
from pydantic import BaseModel


class StatusBreakdownItem(BaseModel):
    status: str
    count: int


class ExecutiveReportTeamMember(BaseModel):
    user_id: int
    full_name: str
    active_task_count: int
    completed_task_count: int


class ExecutiveReportOut(BaseModel):
    project_id: int
    project_name: str
    start_date: datetime
    end_date: datetime
    generated_at: datetime
    total_tasks: int
    completed_tasks: int
    progress_percent: float
    expected_progress_percent: float
    on_schedule: bool
    overdue_tasks: int
    critical_task_count: int
    total_cost: float
    risk_score: float
    risk_level: str
    status_breakdown: list[StatusBreakdownItem]
    team: list[ExecutiveReportTeamMember]


class RecapContributor(BaseModel):
    user_id: int
    full_name: str
    completed_count: int


class RecapOut(BaseModel):
    period: str
    period_start: datetime
    period_end: datetime
    tasks_created: int
    tasks_completed: int
    tasks_overdue: int
    previous_tasks_completed: int
    completed_delta: int
    top_contributors: list[RecapContributor]
