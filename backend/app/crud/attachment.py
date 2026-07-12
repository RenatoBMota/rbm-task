from sqlalchemy.orm import Session
from app.models.attachment import Attachment


def get_attachment(db: Session, attachment_id: int) -> Attachment | None:
    return db.query(Attachment).filter(Attachment.id == attachment_id).first()


def get_attachments(db: Session, task_id: int) -> list[Attachment]:
    return db.query(Attachment).filter(Attachment.task_id == task_id).order_by(Attachment.created_at).all()


def create_attachment(
    db: Session,
    task_id: int,
    uploaded_by_id: int,
    filename: str,
    object_key: str,
    content_type: str | None,
    size_bytes: int,
) -> Attachment:
    attachment = Attachment(
        filename=filename,
        object_key=object_key,
        content_type=content_type,
        size_bytes=size_bytes,
        task_id=task_id,
        uploaded_by_id=uploaded_by_id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def delete_attachment(db: Session, attachment: Attachment) -> None:
    db.delete(attachment)
    db.commit()
