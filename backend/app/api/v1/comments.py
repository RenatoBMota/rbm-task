from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.api.access import require_task_access
from app.crud.comment import get_comments, create_comment
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentOut

router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["comments"])


@router.get("", response_model=list[CommentOut])
def list_comments(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_task_access(db, task_id, current_user.id)
    return get_comments(db, task_id)


@router.post("", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def create(
    task_id: int,
    comment_in: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = require_task_access(db, task_id, current_user.id)
    return create_comment(db, task, current_user.id, comment_in)
