from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.crud.workspace import (
    get_workspace, get_member, get_user_workspaces, create_workspace, update_workspace,
    delete_workspace, list_members, add_member_by_email, update_member_role, remove_member,
)
from app.models.user import User
from app.models.workspace import WorkspaceRole, WorkspaceMember
from app.schemas.workspace import (
    WorkspaceCreate, WorkspaceUpdate, WorkspaceOut, WorkspaceMemberAdd,
    WorkspaceMemberRoleUpdate, WorkspaceMemberOut,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

MANAGE_ROLES = {WorkspaceRole.OWNER, WorkspaceRole.ADMIN}


def _require_member(db: Session, workspace_id: int, user_id: int) -> WorkspaceMember:
    member = get_member(db, workspace_id, user_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Área de trabalho não encontrada")
    return member


def _require_manager(db: Session, workspace_id: int, user_id: int) -> WorkspaceMember:
    member = _require_member(db, workspace_id, user_id)
    if member.role not in MANAGE_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requer perfil de owner/admin na área de trabalho")
    return member


def _get_member_or_404(db: Session, workspace_id: int, member_id: int) -> WorkspaceMember:
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.id == member_id, WorkspaceMember.workspace_id == workspace_id
    ).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membro não encontrado")
    return member


def _workspace_out(workspace, my_role: WorkspaceRole) -> WorkspaceOut:
    return WorkspaceOut(
        id=workspace.id, name=workspace.name, color=workspace.color, icon=workspace.icon,
        owner_id=workspace.owner_id, created_at=workspace.created_at, my_role=my_role,
    )


def _member_out(member: WorkspaceMember) -> WorkspaceMemberOut:
    return WorkspaceMemberOut(
        id=member.id, user_id=member.user_id, email=member.user.email,
        full_name=member.user.full_name, role=member.role,
    )


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspaces = get_user_workspaces(db, current_user.id)
    return [_workspace_out(w, get_member(db, w.id, current_user.id).role) for w in workspaces]


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def create(
    workspace_in: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = create_workspace(db, workspace_in, owner_id=current_user.id)
    return _workspace_out(workspace, WorkspaceRole.OWNER)


@router.get("/{workspace_id}", response_model=WorkspaceOut)
def get(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    member = _require_member(db, workspace_id, current_user.id)
    return _workspace_out(get_workspace(db, workspace_id), member.role)


@router.put("/{workspace_id}", response_model=WorkspaceOut)
def update(
    workspace_id: int,
    workspace_in: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    member = _require_manager(db, workspace_id, current_user.id)
    workspace = update_workspace(db, get_workspace(db, workspace_id), workspace_in)
    return _workspace_out(workspace, member.role)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = get_workspace(db, workspace_id)
    if not workspace or workspace.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Área de trabalho não encontrada")
    delete_workspace(db, workspace)


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberOut])
def get_members(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_member(db, workspace_id, current_user.id)
    return [_member_out(m) for m in list_members(db, workspace_id)]


@router.post("/{workspace_id}/members", response_model=WorkspaceMemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    workspace_id: int,
    member_in: WorkspaceMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_manager(db, workspace_id, current_user.id)
    try:
        member = add_member_by_email(db, workspace_id, member_in.email, member_in.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return _member_out(member)


@router.put("/{workspace_id}/members/{member_id}", response_model=WorkspaceMemberOut)
def change_member_role(
    workspace_id: int,
    member_id: int,
    role_in: WorkspaceMemberRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_manager(db, workspace_id, current_user.id)
    member = _get_member_or_404(db, workspace_id, member_id)
    return _member_out(update_member_role(db, member, role_in.role))


@router.delete("/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    workspace_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_manager(db, workspace_id, current_user.id)
    member = _get_member_or_404(db, workspace_id, member_id)
    if member.role == WorkspaceRole.OWNER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não é possível remover o owner")
    remove_member(db, member)
