from pydantic import BaseModel
from app.models.task_dependency import DependencyType, DependencyHardness


class TaskDependencyCreate(BaseModel):
    depends_on_id: int
    dependency_type: DependencyType = DependencyType.FINISH_START
    lag_days: int = 0
    hardness: DependencyHardness = DependencyHardness.STRONG


class TaskDependencyUpdate(BaseModel):
    dependency_type: DependencyType | None = None
    lag_days: int | None = None
    hardness: DependencyHardness | None = None


class TaskDependencyOut(BaseModel):
    id: int
    task_id: int
    depends_on_id: int
    depends_on_title: str
    depends_on_completed: bool
    dependency_type: DependencyType
    lag_days: int
    hardness: DependencyHardness
