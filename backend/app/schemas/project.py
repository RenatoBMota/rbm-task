from datetime import datetime
from pydantic import BaseModel, model_validator


class ProjectBase(BaseModel):
    name: str
    description: str | None = None
    start_date: datetime
    end_date: datetime
    color: str = "#6366f1"
    icon: str = "folder"
    is_template: bool = False

    @model_validator(mode="after")
    def _check_date_order(self):
        if self.end_date < self.start_date:
            raise ValueError("A data de término não pode ser anterior à data de início.")
        return self


class ProjectCreate(ProjectBase):
    workspace_id: int


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
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
