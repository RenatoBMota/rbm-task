from pydantic import BaseModel


class ChecklistItemBase(BaseModel):
    title: str


class ChecklistItemCreate(ChecklistItemBase):
    pass


class ChecklistItemUpdate(BaseModel):
    title: str | None = None
    is_completed: bool | None = None
    position: int | None = None


class ChecklistItemOut(ChecklistItemBase):
    id: int
    is_completed: bool
    position: int
    task_id: int

    model_config = {"from_attributes": True}
