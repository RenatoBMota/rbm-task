from sqlalchemy.orm import Session
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.user import User
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate


def get_workspace(db: Session, workspace_id: int) -> Workspace | None:
    return db.query(Workspace).filter(Workspace.id == workspace_id).first()


def get_member(db: Session, workspace_id: int, user_id: int) -> WorkspaceMember | None:
    return db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id
    ).first()


def get_user_workspaces(db: Session, user_id: int) -> list[Workspace]:
    return (
        db.query(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .filter(WorkspaceMember.user_id == user_id)
        .all()
    )


def create_workspace(db: Session, workspace_in: WorkspaceCreate, owner_id: int) -> Workspace:
    workspace = Workspace(**workspace_in.model_dump(), owner_id=owner_id)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=owner_id, role=WorkspaceRole.OWNER))
    db.commit()
    db.refresh(workspace)
    return workspace


def update_workspace(db: Session, workspace: Workspace, workspace_in: WorkspaceUpdate) -> Workspace:
    for field, value in workspace_in.model_dump(exclude_unset=True).items():
        setattr(workspace, field, value)
    db.commit()
    db.refresh(workspace)
    return workspace


def delete_workspace(db: Session, workspace: Workspace) -> None:
    db.delete(workspace)
    db.commit()


def list_members(db: Session, workspace_id: int) -> list[WorkspaceMember]:
    return db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).all()


def add_member_by_email(
    db: Session, workspace_id: int, email: str, role: WorkspaceRole
) -> WorkspaceMember:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise ValueError("Usuário não encontrado")
    existing = get_member(db, workspace_id, user.id)
    if existing:
        return existing
    member = WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role=role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def update_member_role(db: Session, member: WorkspaceMember, role: WorkspaceRole) -> WorkspaceMember:
    member.role = role
    db.commit()
    db.refresh(member)
    return member


def remove_member(db: Session, member: WorkspaceMember) -> None:
    db.delete(member)
    db.commit()
