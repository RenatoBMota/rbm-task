from pydantic import BaseModel


class ResourceCreate(BaseModel):
    name: str
    role: str | None = None
    email: str | None = None
    standard_rate: float = 0


class ResourceUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    email: str | None = None
    standard_rate: float | None = None


class ResourceOut(BaseModel):
    id: int
    name: str
    role: str | None
    email: str | None
    standard_rate: float
    workspace_id: int

    model_config = {"from_attributes": True}


class ResourceAssignmentCreate(BaseModel):
    resource_id: int
    allocation_percent: int = 100
    is_coordinator: bool = False


class ResourceAssignmentUpdate(BaseModel):
    allocation_percent: int | None = None
    is_coordinator: bool | None = None


class ResourceAssignmentOut(BaseModel):
    id: int
    task_id: int
    resource_id: int
    resource_name: str
    standard_rate: float
    allocation_percent: int
    is_coordinator: bool


class ResourceUtilization(BaseModel):
    resource_id: int
    resource_name: str
    total_allocation_percent: int
    task_count: int
