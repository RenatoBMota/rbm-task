from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.crud.project import (
    get_project, get_projects, create_project, update_project, delete_project, duplicate_project,
)
from app.crud.workspace import get_member
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut, ProjectDuplicate

router = APIRouter(prefix="/projects", tags=["projects"])


def _require_workspace_member(db: Session, workspace_id: int, user_id: int) -> None:
    if not get_member(db, workspace_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Área de trabalho não encontrada")


def _get_project_with_access(db: Session, project_id: int, user_id: int):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    _require_workspace_member(db, project.workspace_id, user_id)
    return project


@router.get("/", response_model=list[ProjectOut])
def list_projects(
    workspace_id: int,
    skip: int = 0,
    limit: int = 100,
    include_archived: bool = False,
    templates_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_workspace_member(db, workspace_id, current_user.id)
    return get_projects(
        db, workspace_id=workspace_id, skip=skip, limit=limit,
        include_archived=include_archived, templates_only=templates_only,
    )


@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_workspace_member(db, project_in.workspace_id, current_user.id)
    return create_project(db, project_in, owner_id=current_user.id)


@router.get("/{project_id}", response_model=ProjectOut)
def get(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_project_with_access(db, project_id, current_user.id)


@router.put("/{project_id}", response_model=ProjectOut)
def update(
    project_id: int,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_with_access(db, project_id, current_user.id)
    return update_project(db, project, project_in)


@router.post("/{project_id}/duplicate", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def duplicate(
    project_id: int,
    duplicate_in: ProjectDuplicate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_with_access(db, project_id, current_user.id)
    return duplicate_project(db, project, duplicate_in.name, owner_id=current_user.id)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_with_access(db, project_id, current_user.id)
    delete_project(db, project)
