from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.sla_policy import SLAPolicy
from app.models.task import Task, TaskPriority

DEFAULT_TARGET_HOURS: dict[TaskPriority, int] = {
    TaskPriority.P1: 4,
    TaskPriority.P2: 24,
    TaskPriority.P3: 72,
    TaskPriority.P4: 168,
}


def get_policies(db: Session) -> list[SLAPolicy]:
    return db.query(SLAPolicy).all()


def get_target_hours(db: Session, priority: TaskPriority) -> int:
    policy = db.query(SLAPolicy).filter(SLAPolicy.priority == priority).first()
    return policy.target_hours if policy else DEFAULT_TARGET_HOURS[priority]


def upsert_policy(db: Session, priority: TaskPriority, target_hours: int) -> SLAPolicy:
    policy = db.query(SLAPolicy).filter(SLAPolicy.priority == priority).first()
    if policy:
        policy.target_hours = target_hours
    else:
        policy = SLAPolicy(priority=priority, target_hours=target_hours)
        db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def sla_deadline(db: Session, task: Task) -> datetime:
    if task.due_date:
        return _as_utc(task.due_date)
    target_hours = get_target_hours(db, task.priority)
    return _as_utc(task.created_at) + timedelta(hours=target_hours)


def sla_status(db: Session, task: Task) -> str:
    deadline = sla_deadline(db, task)
    now = datetime.now(timezone.utc)
    created_at = _as_utc(task.created_at)

    if task.is_completed:
        completed_at = _as_utc(task.completed_at) if task.completed_at else now
        return "completed_on_time" if completed_at <= deadline else "completed_late"

    if now > deadline:
        return "breached"

    time_left = deadline - now
    total_window = deadline - created_at
    if total_window.total_seconds() > 0 and time_left.total_seconds() / total_window.total_seconds() <= 0.2:
        return "at_risk"
    return "on_time"
