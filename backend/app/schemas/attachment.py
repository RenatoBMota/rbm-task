from datetime import datetime
from pydantic import BaseModel


class AttachmentOut(BaseModel):
    id: int
    filename: str
    content_type: str | None
    size_bytes: int | None
    task_id: int
    uploaded_by_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AttachmentDownloadURL(BaseModel):
    url: str
