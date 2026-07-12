from datetime import datetime
from pydantic import BaseModel


class TaskHistoryOut(BaseModel):
    id: int
    field_name: str
    old_value: str | None
    new_value: str | None
    changed_by_id: int | None
    changed_at: datetime

    model_config = {"from_attributes": True}
