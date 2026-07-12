from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.task import Task
from app.models.user import User, UserRole
from app.crud.sla import sla_status


def scoped_tasks_query(db: Session, user: User, project_id: int | None):
    query = db.query(Task).filter(Task.parent_id == None)
    if user.role != UserRole.ADMIN:
        query = query.filter(Task.assignee_id == user.id)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    return query


def completion_trend(db: Session, user: User, project_id: int | None, days: int) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    tasks = scoped_tasks_query(db, user, project_id).filter(
        Task.is_completed == True, Task.completed_at >= since
    ).all()

    counts: dict[str, int] = {}
    for task in tasks:
        day = task.completed_at.date().isoformat()
        counts[day] = counts.get(day, 0) + 1

    result = []
    for offset in range(days, -1, -1):
        day = (datetime.now(timezone.utc) - timedelta(days=offset)).date().isoformat()
        result.append({"date": day, "completed": counts.get(day, 0)})
    return result


def status_breakdown(db: Session, user: User, project_id: int | None) -> list[dict]:
    tasks = scoped_tasks_query(db, user, project_id).all()
    counts: dict[str, int] = {}
    for task in tasks:
        counts[task.status.value] = counts.get(task.status.value, 0) + 1
    return [{"status": status, "count": count} for status, count in counts.items()]


def sla_compliance(db: Session, user: User, project_id: int | None) -> dict:
    tasks = scoped_tasks_query(db, user, project_id).all()
    total = len(tasks)
    if total == 0:
        return {"total": 0, "on_time": 0, "breached": 0, "at_risk": 0, "compliance_pct": 100.0}

    counts = {"completed_on_time": 0, "completed_late": 0, "on_time": 0, "at_risk": 0, "breached": 0}
    for task in tasks:
        status = sla_status(db, task)
        counts[status] = counts.get(status, 0) + 1

    on_time = counts["completed_on_time"] + counts["on_time"]
    breached = counts["completed_late"] + counts["breached"]
    at_risk = counts["at_risk"]
    compliance_pct = round((on_time / total) * 100, 1)
    return {"total": total, "on_time": on_time, "breached": breached, "at_risk": at_risk, "compliance_pct": compliance_pct}
