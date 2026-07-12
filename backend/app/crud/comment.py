import re
from sqlalchemy.orm import Session
from app.models.comment import Comment
from app.models.task import Task
from app.models.notification import NotificationType
from app.crud.user import get_user_by_email
from app.crud.notification import create_notification
from app.schemas.comment import CommentCreate

MENTION_RE = re.compile(r"@([\w.+-]+@[\w-]+\.[\w.-]+)")


def get_comments(db: Session, task_id: int) -> list[Comment]:
    return db.query(Comment).filter(Comment.task_id == task_id).order_by(Comment.created_at).all()


def create_comment(db: Session, task: Task, author_id: int, comment_in: CommentCreate) -> Comment:
    comment = Comment(content=comment_in.content, task_id=task.id, author_id=author_id)
    db.add(comment)
    db.commit()
    db.refresh(comment)

    notified_user_ids = {author_id}
    for email in MENTION_RE.findall(comment_in.content):
        mentioned = get_user_by_email(db, email)
        if mentioned and mentioned.id not in notified_user_ids:
            create_notification(
                db,
                user_id=mentioned.id,
                type=NotificationType.COMMENT_MENTION,
                message=f"Você foi mencionado em um comentário na tarefa \"{task.title}\"",
                task_id=task.id,
            )
            notified_user_ids.add(mentioned.id)

    if task.assignee_id and task.assignee_id not in notified_user_ids:
        create_notification(
            db,
            user_id=task.assignee_id,
            type=NotificationType.NEW_COMMENT,
            message=f"Novo comentário na tarefa \"{task.title}\"",
            task_id=task.id,
        )

    return comment
