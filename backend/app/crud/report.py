from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.task import Task
from app.models.project import Project
from app.models.task_dependency import TaskDependency
from app.models.user import User
from app.core.critical_path import compute_critical_path
from app.core.predictive_engine import project_risk
from app.crud.task import get_all_project_tasks
from app.crud.resource import task_cost


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def build_executive_report(db: Session, project: Project) -> dict:
    tasks = get_all_project_tasks(db, project.id)
    now = datetime.now(timezone.utc)

    total = len(tasks)
    completed = sum(1 for t in tasks if t.is_completed)
    progress_percent = round(completed / total * 100, 1) if total else 0.0

    overdue = sum(
        1 for t in tasks if t.due_date and not t.is_completed and _aware(t.due_date) < now
    )

    task_ids = [t.id for t in tasks]
    dependencies = (
        db.query(TaskDependency)
        .filter(TaskDependency.task_id.in_(task_ids), TaskDependency.depends_on_id.in_(task_ids))
        .all()
        if task_ids
        else []
    )
    critical_ids = compute_critical_path(tasks, dependencies)

    total_cost = round(sum(task_cost(t) for t in tasks), 2)
    risk = project_risk(db, project.id)

    status_counts: dict[str, int] = {}
    for t in tasks:
        status_counts[t.status.value] = status_counts.get(t.status.value, 0) + 1
    status_breakdown = [{"status": k, "count": v} for k, v in status_counts.items()]

    assignee_ids = {t.assignee_id for t in tasks if t.assignee_id}
    team = []
    if assignee_ids:
        users_by_id = {u.id: u for u in db.query(User).filter(User.id.in_(assignee_ids)).all()}
        for uid in assignee_ids:
            user_tasks = [t for t in tasks if t.assignee_id == uid]
            user = users_by_id.get(uid)
            team.append({
                "user_id": uid,
                "full_name": user.full_name if user else "?",
                "active_task_count": sum(1 for t in user_tasks if not t.is_completed),
                "completed_task_count": sum(1 for t in user_tasks if t.is_completed),
            })
        team.sort(key=lambda r: r["active_task_count"], reverse=True)

    start = _aware(project.start_date)
    end = _aware(project.end_date)
    total_span = (end - start).total_seconds()
    expected_progress = 0.0
    if total_span > 0:
        elapsed = (now - start).total_seconds()
        expected_progress = round(min(max(elapsed / total_span, 0), 1) * 100, 1)

    return {
        "project_id": project.id,
        "project_name": project.name,
        "start_date": project.start_date,
        "end_date": project.end_date,
        "generated_at": now,
        "total_tasks": total,
        "completed_tasks": completed,
        "progress_percent": progress_percent,
        "expected_progress_percent": expected_progress,
        "on_schedule": progress_percent >= expected_progress - 10,
        "overdue_tasks": overdue,
        "critical_task_count": len(critical_ids),
        "total_cost": total_cost,
        "risk_score": risk["risk_score"],
        "risk_level": risk["level"],
        "status_breakdown": status_breakdown,
        "team": team,
    }


def _period_bounds(period: str, now: datetime) -> tuple[datetime, datetime, datetime, datetime]:
    if period == "daily":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        length = now - start
    elif period == "weekly":
        length = timedelta(days=7)
        start = now - length
    elif period == "monthly":
        length = timedelta(days=30)
        start = now - length
    else:
        raise ValueError("invalid period")
    return start, now, start - length, start


def build_recap(db: Session, workspace_id: int, period: str) -> dict:
    now = datetime.now(timezone.utc)
    start, end, prev_start, prev_end = _period_bounds(period, now)
    project_ids = [p.id for p in db.query(Project.id).filter(Project.workspace_id == workspace_id).all()]

    if not project_ids:
        return {
            "period": period, "period_start": start, "period_end": end,
            "tasks_created": 0, "tasks_completed": 0, "tasks_overdue": 0,
            "previous_tasks_completed": 0, "completed_delta": 0, "top_contributors": [],
        }

    def count_created(a: datetime, b: datetime) -> int:
        return db.query(Task).filter(
            Task.project_id.in_(project_ids), Task.created_at >= a, Task.created_at < b
        ).count()

    def count_completed(a: datetime, b: datetime) -> int:
        return db.query(Task).filter(
            Task.project_id.in_(project_ids), Task.is_completed == True,
            Task.completed_at >= a, Task.completed_at < b,
        ).count()

    tasks_created = count_created(start, end)
    tasks_completed = count_completed(start, end)
    prev_completed = count_completed(prev_start, prev_end)

    tasks_overdue = db.query(Task).filter(
        Task.project_id.in_(project_ids), Task.is_completed == False,
        Task.due_date != None, Task.due_date < now,
    ).count()

    contributor_rows = (
        db.query(Task.assignee_id, func.count(Task.id))
        .filter(
            Task.project_id.in_(project_ids), Task.is_completed == True,
            Task.completed_at >= start, Task.completed_at < end, Task.assignee_id != None,
        )
        .group_by(Task.assignee_id)
        .order_by(func.count(Task.id).desc())
        .limit(5)
        .all()
    )
    user_ids = [r[0] for r in contributor_rows]
    users_by_id = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    top_contributors = [
        {
            "user_id": uid,
            "full_name": users_by_id[uid].full_name if uid in users_by_id else "?",
            "completed_count": count,
        }
        for uid, count in contributor_rows
    ]

    return {
        "period": period,
        "period_start": start,
        "period_end": end,
        "tasks_created": tasks_created,
        "tasks_completed": tasks_completed,
        "tasks_overdue": tasks_overdue,
        "previous_tasks_completed": prev_completed,
        "completed_delta": tasks_completed - prev_completed,
        "top_contributors": top_contributors,
    }
