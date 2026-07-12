from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.resource import Resource, ResourceAssignment
from app.models.task import Task
from app.schemas.resource import ResourceCreate, ResourceUpdate


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_resource(db: Session, resource_id: int) -> Resource | None:
    return db.query(Resource).filter(Resource.id == resource_id).first()


def get_resources(db: Session, workspace_id: int) -> list[Resource]:
    return db.query(Resource).filter(Resource.workspace_id == workspace_id).order_by(Resource.name).all()


def create_resource(db: Session, resource_in: ResourceCreate, workspace_id: int) -> Resource:
    resource = Resource(**resource_in.model_dump(), workspace_id=workspace_id)
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def update_resource(db: Session, resource: Resource, resource_in: ResourceUpdate) -> Resource:
    for field, value in resource_in.model_dump(exclude_unset=True).items():
        setattr(resource, field, value)
    db.commit()
    db.refresh(resource)
    return resource


def delete_resource(db: Session, resource: Resource) -> None:
    db.delete(resource)
    db.commit()


def get_assignment(db: Session, assignment_id: int) -> ResourceAssignment | None:
    return db.query(ResourceAssignment).filter(ResourceAssignment.id == assignment_id).first()


def get_task_assignments(db: Session, task_id: int) -> list[ResourceAssignment]:
    return db.query(ResourceAssignment).filter(ResourceAssignment.task_id == task_id).all()


def assign_resource(
    db: Session, task_id: int, resource_id: int, allocation_percent: int, is_coordinator: bool
) -> ResourceAssignment:
    existing = (
        db.query(ResourceAssignment)
        .filter(ResourceAssignment.task_id == task_id, ResourceAssignment.resource_id == resource_id)
        .first()
    )
    if existing:
        existing.allocation_percent = allocation_percent
        existing.is_coordinator = is_coordinator
        db.commit()
        db.refresh(existing)
        return existing
    assignment = ResourceAssignment(
        task_id=task_id,
        resource_id=resource_id,
        allocation_percent=allocation_percent,
        is_coordinator=is_coordinator,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def update_assignment(
    db: Session,
    assignment: ResourceAssignment,
    allocation_percent: int | None,
    is_coordinator: bool | None,
) -> ResourceAssignment:
    if allocation_percent is not None:
        assignment.allocation_percent = allocation_percent
    if is_coordinator is not None:
        assignment.is_coordinator = is_coordinator
    db.commit()
    db.refresh(assignment)
    return assignment


def remove_assignment(db: Session, assignment: ResourceAssignment) -> None:
    db.delete(assignment)
    db.commit()


def task_cost(task: Task) -> float:
    if not task.start_date or not task.due_date or task.is_milestone:
        return 0.0
    duration_days = max((_aware(task.due_date) - _aware(task.start_date)).days, 1)
    return round(
        sum(
            duration_days * a.resource.standard_rate * (a.allocation_percent / 100)
            for a in task.resource_assignments
        ),
        2,
    )


def workspace_resource_utilization(db: Session, workspace_id: int) -> list[dict]:
    resources = get_resources(db, workspace_id)
    now = datetime.now(timezone.utc)
    result = []
    for resource in resources:
        active = [
            a
            for a in resource.assignments
            if a.task.start_date
            and a.task.due_date
            and _aware(a.task.start_date) <= now <= _aware(a.task.due_date)
            and not a.task.is_completed
        ]
        result.append(
            {
                "resource_id": resource.id,
                "resource_name": resource.name,
                "total_allocation_percent": sum(a.allocation_percent for a in active),
                "task_count": len(active),
            }
        )
    return result
