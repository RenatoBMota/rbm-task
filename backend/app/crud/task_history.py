from sqlalchemy.orm import Session
from app.models.task_history import TaskHistory


def record_change(
    db: Session,
    task_id: int,
    field_name: str,
    old_value: str | None,
    new_value: str | None,
    changed_by_id: int | None,
) -> None:
    if old_value == new_value:
        return
    db.add(TaskHistory(
        task_id=task_id,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        changed_by_id=changed_by_id,
    ))
    db.commit()


def get_history(db: Session, task_id: int) -> list[TaskHistory]:
    return (
        db.query(TaskHistory)
        .filter(TaskHistory.task_id == task_id)
        .order_by(TaskHistory.changed_at)
        .all()
    )
