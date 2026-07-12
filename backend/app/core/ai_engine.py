from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.task import Task, TaskPriority
from app.crud.sla import sla_status, sla_deadline

PRIORITY_WEIGHT: dict[TaskPriority, int] = {
    TaskPriority.P1: 40,
    TaskPriority.P2: 30,
    TaskPriority.P3: 20,
    TaskPriority.P4: 10,
}


def _urgency_bonus(task: Task, now: datetime) -> tuple[int, str]:
    if not task.due_date:
        return 0, "sem prazo definido"
    due_date = task.due_date if task.due_date.tzinfo else task.due_date.replace(tzinfo=timezone.utc)
    delta = due_date - now
    hours_left = delta.total_seconds() / 3600
    if hours_left < 0:
        return 100, "prazo já vencido"
    if hours_left <= 24:
        return 50, "vence nas próximas 24h"
    if hours_left <= 72:
        return 20, "vence em até 3 dias"
    return 0, "prazo confortável"


def priority_suggestions(tasks: list[Task], limit: int = 10) -> list[dict]:
    now = datetime.now(timezone.utc)
    scored = []
    for task in tasks:
        urgency, reason = _urgency_bonus(task, now)
        score = PRIORITY_WEIGHT[task.priority] + urgency
        scored.append({
            "task_id": task.id,
            "title": task.title,
            "score": score,
            "reason": f"{task.priority.value} · {reason}",
        })
    scored.sort(key=lambda s: s["score"], reverse=True)
    return scored[:limit]


def estimate_minutes(db: Session, project_id: int | None, priority: TaskPriority | None) -> dict:
    query = db.query(Task).filter(Task.is_completed == True, Task.completed_at != None)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    if priority:
        query = query.filter(Task.priority == priority)

    completed = query.all()
    durations = [
        (t.completed_at - t.created_at).total_seconds() / 60
        for t in completed
        if t.completed_at and t.created_at
    ]
    if durations:
        return {"estimated_minutes": round(sum(durations) / len(durations)), "sample_size": len(durations)}

    estimates = [t.estimated_minutes for t in completed if t.estimated_minutes]
    if estimates:
        return {"estimated_minutes": round(sum(estimates) / len(estimates)), "sample_size": len(estimates)}

    return {"estimated_minutes": None, "sample_size": 0}


def risk_tasks(db: Session, tasks: list[Task]) -> list[dict]:
    risky = []
    for task in tasks:
        status = sla_status(db, task)
        if status in ("at_risk", "breached"):
            risky.append({
                "task_id": task.id,
                "title": task.title,
                "risk": status,
                "deadline": sla_deadline(db, task),
            })
    risky.sort(key=lambda r: r["deadline"])
    return risky
