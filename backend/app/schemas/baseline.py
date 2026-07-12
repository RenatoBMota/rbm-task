from datetime import datetime
from pydantic import BaseModel


class GanttBaselineCreate(BaseModel):
    name: str


class GanttBaselineTaskOut(BaseModel):
    task_id: int | None
    title: str
    start_date: datetime | None
    due_date: datetime | None

    model_config = {"from_attributes": True}


class GanttBaselineOut(BaseModel):
    id: int
    project_id: int
    name: str
    created_at: datetime
    tasks: list[GanttBaselineTaskOut] = []

    model_config = {"from_attributes": True}


class GanttBaselineSummary(BaseModel):
    id: int
    project_id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
