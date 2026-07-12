from pydantic import BaseModel
from app.models.task_dependency import DependencyType, DependencyHardness
from app.schemas.task import TaskOut


class GanttDependency(BaseModel):
    id: int
    task_id: int
    depends_on_id: int
    dependency_type: DependencyType
    lag_days: int
    hardness: DependencyHardness

    model_config = {"from_attributes": True}


class GanttData(BaseModel):
    tasks: list[TaskOut]
    dependencies: list[GanttDependency]
    critical_task_ids: list[int]
