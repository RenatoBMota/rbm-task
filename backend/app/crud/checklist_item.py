from sqlalchemy.orm import Session
from app.models.checklist_item import ChecklistItem
from app.schemas.checklist_item import ChecklistItemCreate, ChecklistItemUpdate


def get_checklist_item(db: Session, item_id: int) -> ChecklistItem | None:
    return db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()


def get_checklist_items(db: Session, task_id: int) -> list[ChecklistItem]:
    return (
        db.query(ChecklistItem)
        .filter(ChecklistItem.task_id == task_id)
        .order_by(ChecklistItem.position)
        .all()
    )


def create_checklist_item(db: Session, task_id: int, item_in: ChecklistItemCreate) -> ChecklistItem:
    position = db.query(ChecklistItem).filter(ChecklistItem.task_id == task_id).count()
    db_item = ChecklistItem(title=item_in.title, task_id=task_id, position=position)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_checklist_item(db: Session, item: ChecklistItem, item_in: ChecklistItemUpdate) -> ChecklistItem:
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_checklist_item(db: Session, item: ChecklistItem) -> None:
    db.delete(item)
    db.commit()
