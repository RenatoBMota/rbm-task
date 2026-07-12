from datetime import datetime
from pydantic import BaseModel
from app.models.task import TaskPriority, TaskStatus, TaskRecurrence
from app.schemas.label import LabelOut


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
    recurrence: TaskRecurrence = TaskRecurrence.NONE
    location: str | None = None


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
    position: int | None = None
    recurrence: TaskRecurrence | None = None
    location: str | None = None
    is_archived: bool | None = None


class TaskMove(BaseModel):
    status: TaskStatus
    position: int


class TaskOut(TaskBase):
    id: int
    is_completed: bool
    completed_at: datetime | None
    position: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    subtask_count: int = 0
    labels: list[LabelOut] = []

    model_config = {"from_attributes": True}


class TaskDuplicate(BaseModel):
    title: str | None = None
