from datetime import datetime
from pydantic import BaseModel


class CommentCreate(BaseModel):
    content: str


class CommentOut(BaseModel):
    id: int
    content: str
    task_id: int
    author_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
