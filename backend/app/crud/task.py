from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.task import Task, TaskStatus
from app.models.notification import NotificationType
from app.models.automation import TriggerEvent
from app.crud.notification import create_notification
from app.core.automation_engine import evaluate_and_run
from app.schemas.task import TaskCreate, TaskUpdate


def get_task(db: Session, task_id: int) -> Task | None:
    return db.query(Task).filter(Task.id == task_id).first()


def get_tasks(
    db: Session,
    assignee_id: int | None = None,
    project_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Task]:
    query = db.query(Task).filter(Task.parent_id == None)
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    return query.offset(skip).limit(limit).all()


def get_today_tasks(db: Session, user_id: int) -> list[Task]:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(hour=23, minute=59, second=59)
    return db.query(Task).filter(
        Task.assignee_id == user_id,
        Task.due_date >= today_start,
        Task.due_date <= today_end,
        Task.is_completed == False,
    ).all()


def get_subtasks(db: Session, parent_id: int) -> list[Task]:
    return db.query(Task).filter(Task.parent_id == parent_id).order_by(Task.position).all()


def get_board_tasks(db: Session, project_id: int) -> list[Task]:
    return (
        db.query(Task)
        .filter(Task.project_id == project_id, Task.parent_id == None)
        .order_by(Task.status, Task.position)
        .all()
    )


def get_overdue_tasks(db: Session, user_id: int) -> list[Task]:
    now = datetime.now(timezone.utc)
    return db.query(Task).filter(
        Task.assignee_id == user_id,
        Task.due_date < now,
        Task.is_completed == False,
    ).all()


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
    evaluate_and_run(db, TriggerEvent.TASK_CREATED, db_task)
    return db_task


def move_task(db: Session, task: Task, status: TaskStatus, position: int) -> Task:
    status_changed = task.status != status
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
        evaluate_and_run(db, TriggerEvent.TASK_STATUS_CHANGED, task)
    return task


def update_task(db: Session, task: Task, task_in: TaskUpdate) -> Task:
    update_data = task_in.model_dump(exclude_unset=True)
    became_completed = update_data.get("is_completed") is True and not task.is_completed
    if became_completed:
        update_data["completed_at"] = datetime.now(timezone.utc)
    elif update_data.get("is_completed") is False:
        update_data["completed_at"] = None

    previous_assignee_id = task.assignee_id
    previous_status = task.status
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
        evaluate_and_run(db, TriggerEvent.TASK_STATUS_CHANGED, task)
    if became_completed:
        evaluate_and_run(db, TriggerEvent.TASK_COMPLETED, task)
    return task


def delete_task(db: Session, task: Task) -> None:
    db.delete(task)
    db.commit()
