from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.api.access import require_project_member
from app.crud.baseline import get_baseline, get_project_baselines, create_baseline, delete_baseline
from app.crud.task import get_all_project_tasks
from app.models.user import User
from app.schemas.baseline import GanttBaselineCreate, GanttBaselineOut, GanttBaselineSummary

router = APIRouter(prefix="/projects/{project_id}/baselines", tags=["baselines"])


@router.get("", response_model=list[GanttBaselineSummary])
def list_baselines(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_member(db, project_id, current_user.id)
    return get_project_baselines(db, project_id)


@router.post("", response_model=GanttBaselineOut, status_code=status.HTTP_201_CREATED)
def create(
    project_id: int,
    baseline_in: GanttBaselineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_member(db, project_id, current_user.id)
    tasks = get_all_project_tasks(db, project_id)
    return create_baseline(db, project_id, baseline_in.name, current_user.id, tasks)


@router.get("/{baseline_id}", response_model=GanttBaselineOut)
def get(
    project_id: int,
    baseline_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_member(db, project_id, current_user.id)
    baseline = get_baseline(db, baseline_id)
    if not baseline or baseline.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Baseline não encontrada")
    return baseline


@router.delete("/{baseline_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    project_id: int,
    baseline_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_member(db, project_id, current_user.id)
    baseline = get_baseline(db, baseline_id)
    if not baseline or baseline.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Baseline não encontrada")
    delete_baseline(db, baseline)
