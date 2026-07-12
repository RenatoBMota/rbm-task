from sqlalchemy.orm import Session
from app.models.notification import Notification, NotificationType


def get_notifications(db: Session, user_id: int, unread_only: bool = False) -> list[Notification]:
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    return query.order_by(Notification.created_at.desc()).all()


def count_unread(db: Session, user_id: int) -> int:
    return db.query(Notification).filter(
        Notification.user_id == user_id, Notification.is_read == False
    ).count()


def create_notification(
    db: Session,
    user_id: int,
    type: NotificationType,
    message: str,
    task_id: int | None = None,
) -> Notification:
    notification = Notification(user_id=user_id, type=type, message=message, task_id=task_id)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def mark_read(db: Session, notification: Notification) -> Notification:
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_read(db: Session, user_id: int) -> None:
    db.query(Notification).filter(
        Notification.user_id == user_id, Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
