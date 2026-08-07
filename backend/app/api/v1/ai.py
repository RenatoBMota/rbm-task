from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.api.access import require_workspace_member
from app.crud.task import get_tasks
from app.core.ai_engine import priority_suggestions, estimate_minutes, risk_tasks
from app.core.ai_task_extraction import (
    suggest_tasks_for_workspace, AiNotConfiguredError, AiRequestError,
)
from app.models.task import TaskPriority
from app.models.user import User
from app.schemas.ai import PrioritySuggestion, TimeEstimate, RiskTask
from app.schemas.ai_tasks import ExtractTasksRequest, TaskSuggestionOut

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/priority-suggestions", response_model=list[PrioritySuggestion])
def get_priority_suggestions(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks = [t for t in get_tasks(db, assignee_id=current_user.id, limit=200) if not t.is_completed]
    return priority_suggestions(tasks, limit)


@router.get("/time-estimate", response_model=TimeEstimate)
def get_time_estimate(
    project_id: int | None = None,
    priority: TaskPriority | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return estimate_minutes(db, project_id, priority)


@router.get("/risk-tasks", response_model=list[RiskTask])
def get_risk_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks = [t for t in get_tasks(db, assignee_id=current_user.id, limit=200) if not t.is_completed]
    return risk_tasks(db, tasks)


@router.post("/extract-tasks", response_model=list[TaskSuggestionOut])
def extract_tasks(
    body: ExtractTasksRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_workspace_member(db, body.workspace_id, current_user.id)
    try:
        return suggest_tasks_for_workspace(db, body.workspace_id, body.text)
    except AiNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except AiRequestError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
