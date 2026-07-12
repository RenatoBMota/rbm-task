from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.crud.analytics import completion_trend, status_breakdown, sla_compliance
from app.models.user import User
from app.schemas.analytics import CompletionTrendPoint, StatusBreakdownItem, SLACompliance

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/completion-trend", response_model=list[CompletionTrendPoint])
def get_completion_trend(
    project_id: int | None = None,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return completion_trend(db, current_user, project_id, days)


@router.get("/status-breakdown", response_model=list[StatusBreakdownItem])
def get_status_breakdown(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return status_breakdown(db, current_user, project_id)


@router.get("/sla-compliance", response_model=SLACompliance)
def get_sla_compliance(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return sla_compliance(db, current_user, project_id)
