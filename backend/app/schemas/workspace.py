from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.models.workspace import WorkspaceRole


class WorkspaceBase(BaseModel):
    name: str
    color: str = "#0079bf"
    icon: str = "briefcase"


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    icon: str | None = None


class WorkspaceOut(WorkspaceBase):
    id: int
    owner_id: int
    created_at: datetime
    my_role: WorkspaceRole | None = None

    model_config = {"from_attributes": True}


class WorkspaceMemberAdd(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.MEMBER


class WorkspaceMemberRoleUpdate(BaseModel):
    role: WorkspaceRole


class WorkspaceMemberOut(BaseModel):
    id: int
    user_id: int
    email: str
    full_name: str
    role: WorkspaceRole

    model_config = {"from_attributes": True}
