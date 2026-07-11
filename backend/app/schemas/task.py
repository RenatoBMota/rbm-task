from datetime import datetime
from pydantic import BaseModel
from app.models.task import TaskPriority, TaskStatus


class TaskBase(BaseModel):
    title: str
    description: str | None = None
    priority: TaskPriority = TaskPriority.P4
    status: TaskStatus = TaskStatus.TODO
    due_date: datetime | None = None
    estimated_minutes: int | None = None
    project_id: int | None = None
    assignee_id: int | None = None
    parent_id: int | None = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    due_date: datetime | None = None
    estimated_minutes: int | None = None
    project_id: int | None = None
    assignee_id: int | None = None
    is_completed: bool | None = None


class TaskOut(TaskBase):
    id: int
    is_completed: bool
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    subtask_count: int = 0

    model_config = {"from_attributes": True}
