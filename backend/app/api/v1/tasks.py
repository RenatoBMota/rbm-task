from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.crud.task import (
    get_task, get_tasks, get_today_tasks, get_overdue_tasks, get_board_tasks,
    create_task, update_task, delete_task, move_task
)
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskOut, TaskMove

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskOut])
def list_tasks(
    project_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_tasks(db, assignee_id=current_user.id, project_id=project_id, skip=skip, limit=limit)


@router.get("/today", response_model=list[TaskOut])
def list_today_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_today_tasks(db, current_user.id)


@router.get("/overdue", response_model=list[TaskOut])
def list_overdue_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_overdue_tasks(db, current_user.id)


@router.get("/board", response_model=list[TaskOut])
def list_board_tasks(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_board_tasks(db, project_id)


@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_task(db, task_in, creator_id=current_user.id)


@router.get("/{task_id}", response_model=TaskOut)
def get(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return task


@router.put("/{task_id}", response_model=TaskOut)
def update(
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return update_task(db, task, task_in)


@router.patch("/{task_id}/move", response_model=TaskOut)
def move(
    task_id: int,
    move_in: TaskMove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return move_task(db, task, move_in.status, move_in.position)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    delete_task(db, task)
