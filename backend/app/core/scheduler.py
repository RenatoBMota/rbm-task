import logging
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.database import SessionLocal
from app.models.task import Task
from app.models.notification import NotificationType
from app.models.automation import TriggerEvent
from app.crud.notification import create_notification
from app.crud.sla import sla_deadline
from app.crud.reminder import get_due_reminders, mark_sent
from app.core.automation_engine import evaluate_and_run

logger = logging.getLogger("rbm.scheduler")

CHECK_INTERVAL_MINUTES = 15
REMINDER_CHECK_INTERVAL_MINUTES = 5


def check_overdue_and_sla() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=CHECK_INTERVAL_MINUTES)

        just_overdue = db.query(Task).filter(
            Task.is_completed == False,
            Task.due_date != None,
            Task.due_date >= window_start,
            Task.due_date < now,
        ).all()
        for task in just_overdue:
            if task.assignee_id:
                create_notification(
                    db,
                    user_id=task.assignee_id,
                    type=NotificationType.NEW_COMMENT,
                    message=f"A tarefa \"{task.title}\" venceu e ainda não foi concluída",
                    task_id=task.id,
                )
            evaluate_and_run(db, TriggerEvent.TASK_OVERDUE, task)

        active_tasks = db.query(Task).filter(Task.is_completed == False).all()
        for task in active_tasks:
            deadline = sla_deadline(db, task)
            if window_start <= deadline < now:
                evaluate_and_run(db, TriggerEvent.SLA_BREACH, task)
    except Exception:
        logger.exception("Falha ao rodar verificação de prazos/SLA")
    finally:
        db.close()


def check_reminders() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        for reminder in get_due_reminders(db, now):
            task = reminder.task
            if task and task.assignee_id:
                create_notification(
                    db,
                    user_id=task.assignee_id,
                    type=NotificationType.NEW_COMMENT,
                    message=f"Lembrete: \"{task.title}\"",
                    task_id=task.id,
                )
            mark_sent(db, reminder)
    except Exception:
        logger.exception("Falha ao rodar verificação de lembretes")
    finally:
        db.close()


scheduler = BackgroundScheduler()


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        check_overdue_and_sla,
        "interval",
        minutes=CHECK_INTERVAL_MINUTES,
        id="check_overdue_and_sla",
        replace_existing=True,
    )
    scheduler.add_job(
        check_reminders,
        "interval",
        minutes=REMINDER_CHECK_INTERVAL_MINUTES,
        id="check_reminders",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
