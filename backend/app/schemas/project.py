from datetime import datetime
from pydantic import BaseModel


class ProjectBase(BaseModel):
    name: str
    description: str | None = None
    color: str = "#6366f1"
    icon: str = "folder"
    is_template: bool = False


class ProjectCreate(ProjectBase):
    workspace_id: int


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None
    icon: str | None = None
    is_archived: bool | None = None
    is_template: bool | None = None


class ProjectOut(ProjectBase):
    id: int
    is_archived: bool
    owner_id: int
    workspace_id: int | None
    created_at: datetime
    updated_at: datetime
    task_count: int = 0

    model_config = {"from_attributes": True}


class ProjectDuplicate(BaseModel):
    name: str
