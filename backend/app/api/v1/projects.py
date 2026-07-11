from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.crud.project import get_project, get_projects, create_project, update_project, delete_project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=list[ProjectOut])
def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_projects(db, owner_id=current_user.id, skip=skip, limit=limit)


@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_project(db, project_in, owner_id=current_user.id)


@router.get("/{project_id}", response_model=ProjectOut)
def get(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project(db, project_id, owner_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return project


@router.put("/{project_id}", response_model=ProjectOut)
def update(
    project_id: int,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project(db, project_id, owner_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return update_project(db, project, project_in)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project(db, project_id, owner_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    delete_project(db, project)
