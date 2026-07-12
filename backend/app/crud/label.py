from sqlalchemy.orm import Session
from app.models.label import Label
from app.models.task import Task
from app.schemas.label import LabelCreate, LabelUpdate


def get_label(db: Session, label_id: int, owner_id: int) -> Label | None:
    return db.query(Label).filter(Label.id == label_id, Label.owner_id == owner_id).first()


def get_labels(db: Session, owner_id: int) -> list[Label]:
    return db.query(Label).filter(Label.owner_id == owner_id).all()


def create_label(db: Session, label_in: LabelCreate, owner_id: int) -> Label:
    label = Label(**label_in.model_dump(), owner_id=owner_id)
    db.add(label)
    db.commit()
    db.refresh(label)
    return label


def update_label(db: Session, label: Label, label_in: LabelUpdate) -> Label:
    for field, value in label_in.model_dump(exclude_unset=True).items():
        setattr(label, field, value)
    db.commit()
    db.refresh(label)
    return label


def delete_label(db: Session, label: Label) -> None:
    db.delete(label)
    db.commit()


def attach_label(db: Session, task: Task, label: Label) -> Task:
    if label not in task.labels:
        task.labels.append(label)
        db.commit()
        db.refresh(task)
    return task


def detach_label(db: Session, task: Task, label: Label) -> Task:
    if label in task.labels:
        task.labels.remove(label)
        db.commit()
        db.refresh(task)
    return task
