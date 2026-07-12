from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.task import Task, TaskPriority
from app.models.project import Project
from app.crud.sla import sla_status
from app.crud.workspace import list_members

LOAD_WEIGHT: dict[TaskPriority, int] = {
    TaskPriority.P1: 4,
    TaskPriority.P2: 3,
    TaskPriority.P3: 2,
    TaskPriority.P4: 1,
}

OVERLOAD_THRESHOLD = 12


def team_workload(db: Session, workspace_id: int) -> list[dict]:
    members = list_members(db, workspace_id)
    project_ids = [p.id for p in db.query(Project.id).filter(Project.workspace_id == workspace_id).all()]

    result = []
    for member in members:
        active_tasks = (
            db.query(Task).filter(
                Task.assignee_id == member.user_id,
                Task.project_id.in_(project_ids),
                Task.is_completed == False,
                Task.parent_id == None,
                Task.is_archived == False,
            ).all()
            if project_ids else []
        )
        weighted_load = sum(LOAD_WEIGHT[t.priority] for t in active_tasks)
        result.append({
            "user_id": member.user_id,
            "full_name": member.user.full_name,
            "active_task_count": len(active_tasks),
            "weighted_load": weighted_load,
            "is_overloaded": weighted_load > OVERLOAD_THRESHOLD,
        })
    result.sort(key=lambda r: r["weighted_load"], reverse=True)
    return result


def project_risk(db: Session, project_id: int) -> dict:
    tasks = db.query(Task).filter(
        Task.project_id == project_id, Task.parent_id == None, Task.is_archived == False
    ).all()
    active_tasks = [t for t in tasks if not t.is_completed]
    total = len(tasks)

    breached = at_risk = overdue = 0
    now = datetime.now(timezone.utc)
    for task in active_tasks:
        status = sla_status(db, task)
        if status == "breached":
            breached += 1
        elif status == "at_risk":
            at_risk += 1
        if task.due_date:
            due_date = task.due_date if task.due_date.tzinfo else task.due_date.replace(tzinfo=timezone.utc)
            if due_date < now:
                overdue += 1

    denominator = max(total, 1)
    raw_score = (breached * 3 + at_risk * 1 + overdue * 2) / denominator * 10
    risk_score = round(min(raw_score, 100), 1)

    if risk_score < 20:
        level = "low"
    elif risk_score < 50:
        level = "medium"
    else:
        level = "high"

    return {
        "project_id": project_id,
        "total_tasks": total,
        "overdue": overdue,
        "at_risk": at_risk,
        "breached": breached,
        "risk_score": risk_score,
        "level": level,
    }
