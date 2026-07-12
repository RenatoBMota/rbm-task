from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.crud.task import get_task
from app.crud.checklist_item import (
    get_checklist_item, get_checklist_items, create_checklist_item,
    update_checklist_item, delete_checklist_item,
)
from app.models.user import User
from app.schemas.checklist_item import ChecklistItemCreate, ChecklistItemUpdate, ChecklistItemOut

router = APIRouter(prefix="/tasks/{task_id}/checklist", tags=["checklist"])


def _get_task_or_404(db: Session, task_id: int):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada")
    return task


@router.get("/", response_model=list[ChecklistItemOut])
def list_items(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_task_or_404(db, task_id)
    return get_checklist_items(db, task_id)


@router.post("/", response_model=ChecklistItemOut, status_code=status.HTTP_201_CREATED)
def create_item(
    task_id: int,
    item_in: ChecklistItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_task_or_404(db, task_id)
    return create_checklist_item(db, task_id, item_in)


@router.put("/{item_id}", response_model=ChecklistItemOut)
def update_item(
    task_id: int,
    item_id: int,
    item_in: ChecklistItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_checklist_item(db, item_id)
    if not item or item.task_id != task_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado")
    return update_checklist_item(db, item, item_in)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    task_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_checklist_item(db, item_id)
    if not item or item.task_id != task_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado")
    delete_checklist_item(db, item)
