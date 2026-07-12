from datetime import datetime
from pydantic import BaseModel
from app.models.task import TaskPriority


class SLAPolicyOut(BaseModel):
    priority: TaskPriority
    target_hours: int

    model_config = {"from_attributes": True}


class SLAPolicyUpdate(BaseModel):
    target_hours: int


class TaskSLAOut(BaseModel):
    status: str
    deadline: datetime
