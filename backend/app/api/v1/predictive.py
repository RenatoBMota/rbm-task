from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.api.access import require_project_member, require_workspace_member
from app.core.predictive_engine import team_workload, project_risk
from app.models.user import User
from app.schemas.ai import TeamWorkload, ProjectRisk

router = APIRouter(prefix="/predictive", tags=["predictive"])


@router.get("/workspaces/{workspace_id}/workload", response_model=list[TeamWorkload])
def get_team_workload(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_workspace_member(db, workspace_id, current_user.id)
    return team_workload(db, workspace_id)


@router.get("/projects/{project_id}/risk", response_model=ProjectRisk)
def get_project_risk(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_member(db, project_id, current_user.id)
    return project_risk(db, project_id)
