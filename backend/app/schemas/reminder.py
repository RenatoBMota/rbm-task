from datetime import datetime
from pydantic import BaseModel


class ReminderCreate(BaseModel):
    remind_at: datetime


class ReminderOut(BaseModel):
    id: int
    task_id: int
    remind_at: datetime
    is_sent: bool

    model_config = {"from_attributes": True}
