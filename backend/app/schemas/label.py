from pydantic import BaseModel


class LabelCreate(BaseModel):
    name: str
    color: str = "#6366f1"


class LabelUpdate(BaseModel):
    name: str | None = None
    color: str | None = None


class LabelOut(BaseModel):
    id: int
    name: str
    color: str

    model_config = {"from_attributes": True}
