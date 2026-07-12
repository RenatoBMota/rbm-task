from sqlalchemy.orm import Session
from app.models.task import Task
from app.models.task_dependency import TaskDependency, DependencyType, DependencyHardness


def get_dependency(db: Session, dependency_id: int) -> TaskDependency | None:
    return db.query(TaskDependency).filter(TaskDependency.id == dependency_id).first()


def get_dependencies(db: Session, task_id: int) -> list[TaskDependency]:
    return db.query(TaskDependency).filter(TaskDependency.task_id == task_id).all()


def add_dependency(
    db: Session,
    task_id: int,
    depends_on_id: int,
    dependency_type: DependencyType = DependencyType.FINISH_START,
    lag_days: int = 0,
    hardness: DependencyHardness = DependencyHardness.STRONG,
) -> TaskDependency:
    if task_id == depends_on_id:
        raise ValueError("Uma tarefa não pode depender de si mesma")
    existing = (
        db.query(TaskDependency)
        .filter(TaskDependency.task_id == task_id, TaskDependency.depends_on_id == depends_on_id)
        .first()
    )
    if existing:
        return existing
    dependency = TaskDependency(
        task_id=task_id,
        depends_on_id=depends_on_id,
        dependency_type=dependency_type,
        lag_days=lag_days,
        hardness=hardness,
    )
    db.add(dependency)
    db.commit()
    db.refresh(dependency)
    return dependency


def update_dependency(
    db: Session,
    dependency: TaskDependency,
    dependency_type: DependencyType | None = None,
    lag_days: int | None = None,
    hardness: DependencyHardness | None = None,
) -> TaskDependency:
    if dependency_type is not None:
        dependency.dependency_type = dependency_type
    if lag_days is not None:
        dependency.lag_days = lag_days
    if hardness is not None:
        dependency.hardness = hardness
    db.commit()
    db.refresh(dependency)
    return dependency


def remove_dependency(db: Session, dependency: TaskDependency) -> None:
    db.delete(dependency)
    db.commit()


def blocking_dependencies(db: Session, task_id: int) -> list[Task]:
    dependency_ids = (
        db.query(TaskDependency.depends_on_id)
        .filter(
            TaskDependency.task_id == task_id,
            TaskDependency.dependency_type == DependencyType.FINISH_START,
        )
        .scalar_subquery()
    )
    return db.query(Task).filter(Task.id.in_(dependency_ids), Task.is_completed == False).all()
