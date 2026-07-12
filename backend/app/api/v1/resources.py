from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.api.access import require_workspace_member
from app.crud.resource import (
    get_resource, get_resources, create_resource, update_resource, delete_resource,
    workspace_resource_utilization,
)
from app.models.user import User
from app.schemas.resource import ResourceCreate, ResourceUpdate, ResourceOut, ResourceUtilization

router = APIRouter(prefix="/workspaces/{workspace_id}/resources", tags=["resources"])


def _require_resource_access(db: Session, resource_id: int, workspace_id: int, user_id: int):
    resource = get_resource(db, resource_id)
    if not resource or resource.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso não encontrado")
    require_workspace_member(db, workspace_id, user_id)
    return resource


@router.get("", response_model=list[ResourceOut])
def list_resources(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_workspace_member(db, workspace_id, current_user.id)
    return get_resources(db, workspace_id)


@router.post("", response_model=ResourceOut, status_code=status.HTTP_201_CREATED)
def create(
    workspace_id: int,
    resource_in: ResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_workspace_member(db, workspace_id, current_user.id)
    return create_resource(db, resource_in, workspace_id)


@router.get("/utilization", response_model=list[ResourceUtilization])
def get_utilization(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_workspace_member(db, workspace_id, current_user.id)
    return workspace_resource_utilization(db, workspace_id)


@router.put("/{resource_id}", response_model=ResourceOut)
def update(
    workspace_id: int,
    resource_id: int,
    resource_in: ResourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource = _require_resource_access(db, resource_id, workspace_id, current_user.id)
    return update_resource(db, resource, resource_in)


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    workspace_id: int,
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource = _require_resource_access(db, resource_id, workspace_id, current_user.id)
    delete_resource(db, resource)
