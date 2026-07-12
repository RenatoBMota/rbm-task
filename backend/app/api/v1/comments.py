from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.crud.task import get_task
from app.crud.comment import get_comments, create_comment
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentOut

router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["comments"])


@router.get("/", response_model=list[CommentOut])
def list_comments(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada")
    return get_comments(db, task_id)


@router.post("/", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def create(
    task_id: int,
    comment_in: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada")
    return create_comment(db, task, current_user.id, comment_in)
