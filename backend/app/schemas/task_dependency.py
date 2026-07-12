from pydantic import BaseModel


class TaskDependencyCreate(BaseModel):
    depends_on_id: int


class TaskDependencyOut(BaseModel):
    id: int
    depends_on_id: int
    depends_on_title: str
    depends_on_completed: bool
