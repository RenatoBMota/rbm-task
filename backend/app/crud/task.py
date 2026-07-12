import calendar
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.task import Task, TaskStatus, TaskRecurrence
from app.models.project import Project
from app.models.notification import NotificationType
from app.models.automation import TriggerEvent
from app.crud.notification import create_notification
from app.crud.task_history import record_change
from app.crud.task_dependency import blocking_dependencies
from app.core.automation_engine import evaluate_and_run
from app.core.exceptions import TaskBlockedError
from app.schemas.task import TaskCreate, TaskUpdate

BLOCKING_STATUSES = {TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW, TaskStatus.DONE}


def _add_months(dt: datetime, months: int = 1) -> datetime:
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _next_due_date(due_date: datetime, recurrence: TaskRecurrence) -> datetime:
    if recurrence == TaskRecurrence.DAILY:
        return due_date + timedelta(days=1)
    if recurrence == TaskRecurrence.WEEKLY:
        return due_date + timedelta(weeks=1)
    return _add_months(due_date, 1)


def _assert_not_blocked(db: Session, task: Task) -> None:
    blockers = blocking_dependencies(db, task.id)
    if blockers:
        raise TaskBlockedError([t.title for t in blockers])


def _create_next_occurrence(db: Session, task: Task) -> Task:
    next_due = _next_due_date(task.due_date, task.recurrence) if task.due_date else None
    next_task = Task(
        title=task.title,
        description=task.description,
        priority=task.priority,
        status=TaskStatus.TODO,
        due_date=next_due,
        estimated_minutes=task.estimated_minutes,
        project_id=task.project_id,
        assignee_id=task.assignee_id,
        parent_id=task.parent_id,
        recurrence=task.recurrence,
    )
    max_position = db.query(Task).filter(Task.status == TaskStatus.TODO).count()
    next_task.position = max_position
    db.add(next_task)
    db.commit()
    db.refresh(next_task)
    return next_task


def get_task(db: Session, task_id: int) -> Task | None:
    return db.query(Task).filter(Task.id == task_id).first()


def _scope_to_workspace(db: Session, query, workspace_id: int | None):
    if workspace_id is None:
        return query
    project_ids = [p.id for p in db.query(Project.id).filter(Project.workspace_id == workspace_id).all()]
    return query.filter(or_(Task.project_id == None, Task.project_id.in_(project_ids)))


def get_tasks(
    db: Session,
    assignee_id: int | None = None,
    project_id: int | None = None,
    workspace_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    include_archived: bool = False,
) -> list[Task]:
    query = db.query(Task).filter(Task.parent_id == None)
    if not include_archived:
        query = query.filter(Task.is_archived == False)
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    query = _scope_to_workspace(db, query, workspace_id)
    return query.offset(skip).limit(limit).all()


def get_today_tasks(db: Session, user_id: int, workspace_id: int | None = None) -> list[Task]:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(hour=23, minute=59, second=59)
    query = db.query(Task).filter(
        Task.assignee_id == user_id,
        Task.due_date >= today_start,
        Task.due_date <= today_end,
        Task.is_completed == False,
    )
    return _scope_to_workspace(db, query, workspace_id).all()


def get_subtasks(db: Session, parent_id: int) -> list[Task]:
    return db.query(Task).filter(Task.parent_id == parent_id).order_by(Task.position).all()


def get_board_tasks(db: Session, project_id: int) -> list[Task]:
    return (
        db.query(Task)
        .filter(Task.project_id == project_id, Task.parent_id == None)
        .order_by(Task.status, Task.position)
        .all()
    )


def get_overdue_tasks(db: Session, user_id: int, workspace_id: int | None = None) -> list[Task]:
    now = datetime.now(timezone.utc)
    query = db.query(Task).filter(
        Task.assignee_id == user_id,
        Task.due_date < now,
        Task.is_completed == False,
    )
    return _scope_to_workspace(db, query, workspace_id).all()


def create_task(db: Session, task_in: TaskCreate, creator_id: int) -> Task:
    db_task = Task(**task_in.model_dump())
    if not db_task.assignee_id:
        db_task.assignee_id = creator_id
    max_position = db.query(Task).filter(Task.status == db_task.status).count()
    db_task.position = max_position
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    if db_task.assignee_id != creator_id:
        create_notification(
            db,
            user_id=db_task.assignee_id,
            type=NotificationType.TASK_ASSIGNED,
            message=f"Você foi designado para a tarefa \"{db_task.title}\"",
            task_id=db_task.id,
        )
    record_change(db, db_task.id, "created", None, db_task.title, creator_id)
    evaluate_and_run(db, TriggerEvent.TASK_CREATED, db_task)
    return db_task


def move_task(db: Session, task: Task, status: TaskStatus, position: int, changed_by_id: int | None = None) -> Task:
    if status in BLOCKING_STATUSES and status != task.status:
        _assert_not_blocked(db, task)

    status_changed = task.status != status
    previous_status = task.status
    siblings = (
        db.query(Task)
        .filter(Task.status == status, Task.id != task.id)
        .order_by(Task.position)
        .all()
    )
    siblings.insert(min(position, len(siblings)), task)
    for index, sibling in enumerate(siblings):
        sibling.status = status
        sibling.position = index
    db.commit()
    db.refresh(task)
    if status_changed:
        record_change(db, task.id, "status", previous_status.value, status.value, changed_by_id)
        evaluate_and_run(db, TriggerEvent.TASK_STATUS_CHANGED, task)
    return task


def update_task(db: Session, task: Task, task_in: TaskUpdate, changed_by_id: int | None = None) -> Task:
    update_data = task_in.model_dump(exclude_unset=True)
    became_completed = update_data.get("is_completed") is True and not task.is_completed
    target_status = update_data.get("status", task.status)
    wants_progress = became_completed or target_status in BLOCKING_STATUSES

    if wants_progress and (became_completed or target_status != task.status):
        _assert_not_blocked(db, task)

    if became_completed:
        update_data["completed_at"] = datetime.now(timezone.utc)
    elif update_data.get("is_completed") is False:
        update_data["completed_at"] = None

    previous_assignee_id = task.assignee_id
    previous_status = task.status
    previous_priority = task.priority
    previous_due_date = task.due_date
    new_assignee_id = update_data.get("assignee_id", previous_assignee_id)

    for field, value in update_data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)

    if new_assignee_id and new_assignee_id != previous_assignee_id:
        create_notification(
            db,
            user_id=new_assignee_id,
            type=NotificationType.TASK_ASSIGNED,
            message=f"Você foi designado para a tarefa \"{task.title}\"",
            task_id=task.id,
        )
    if task.status != previous_status:
        record_change(db, task.id, "status", previous_status.value, task.status.value, changed_by_id)
        evaluate_and_run(db, TriggerEvent.TASK_STATUS_CHANGED, task)
    if task.priority != previous_priority:
        record_change(db, task.id, "priority", previous_priority.value, task.priority.value, changed_by_id)
    if task.due_date != previous_due_date:
        record_change(
            db, task.id, "due_date",
            previous_due_date.isoformat() if previous_due_date else None,
            task.due_date.isoformat() if task.due_date else None,
            changed_by_id,
        )
    if became_completed:
        evaluate_and_run(db, TriggerEvent.TASK_COMPLETED, task)
        if task.recurrence != TaskRecurrence.NONE:
            _create_next_occurrence(db, task)
    return task


def delete_task(db: Session, task: Task) -> None:
    db.delete(task)
    db.commit()


def duplicate_task(db: Session, task: Task, title: str | None, creator_id: int) -> Task:
    max_position = db.query(Task).filter(Task.status == TaskStatus.TODO).count()
    new_task = Task(
        title=title or f"{task.title} (cópia)",
        description=task.description,
        priority=task.priority,
        status=TaskStatus.TODO,
        due_date=task.due_date,
        estimated_minutes=task.estimated_minutes,
        project_id=task.project_id,
        assignee_id=task.assignee_id or creator_id,
        parent_id=task.parent_id,
        recurrence=task.recurrence,
        location=task.location,
        position=max_position,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


def archive_task(db: Session, task: Task, is_archived: bool) -> Task:
    task.is_archived = is_archived
    db.commit()
    db.refresh(task)
    return task
