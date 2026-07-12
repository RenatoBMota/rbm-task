from sqlalchemy.orm import Session
from app.models.reminder import Reminder


def get_reminder(db: Session, reminder_id: int) -> Reminder | None:
    return db.query(Reminder).filter(Reminder.id == reminder_id).first()


def get_reminders(db: Session, task_id: int) -> list[Reminder]:
    return db.query(Reminder).filter(Reminder.task_id == task_id).order_by(Reminder.remind_at).all()


def create_reminder(db: Session, task_id: int, remind_at) -> Reminder:
    reminder = Reminder(task_id=task_id, remind_at=remind_at)
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


def delete_reminder(db: Session, reminder: Reminder) -> None:
    db.delete(reminder)
    db.commit()


def get_due_reminders(db: Session, now):
    return db.query(Reminder).filter(Reminder.remind_at <= now, Reminder.is_sent == False).all()


def mark_sent(db: Session, reminder: Reminder) -> None:
    reminder.is_sent = True
    db.commit()
