from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.crud.label import get_label, get_labels, create_label, update_label, delete_label
from app.models.user import User
from app.schemas.label import LabelCreate, LabelUpdate, LabelOut

router = APIRouter(prefix="/labels", tags=["labels"])


@router.get("", response_model=list[LabelOut])
def list_labels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_labels(db, owner_id=current_user.id)


@router.post("", response_model=LabelOut, status_code=status.HTTP_201_CREATED)
def create(
    label_in: LabelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_label(db, label_in, owner_id=current_user.id)


@router.put("/{label_id}", response_model=LabelOut)
def update(
    label_id: int,
    label_in: LabelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    label = get_label(db, label_id, owner_id=current_user.id)
    if not label:
        raise HTTPException(status_code=404, detail="Etiqueta não encontrada")
    return update_label(db, label, label_in)


@router.delete("/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    label_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    label = get_label(db, label_id, owner_id=current_user.id)
    if not label:
        raise HTTPException(status_code=404, detail="Etiqueta não encontrada")
    delete_label(db, label)
