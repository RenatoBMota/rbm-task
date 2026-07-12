from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin
from app.crud.task import get_task
from app.crud.sla import get_policies, upsert_policy, sla_status, sla_deadline, DEFAULT_TARGET_HOURS
from app.models.task import TaskPriority
from app.models.user import User
from app.schemas.sla import SLAPolicyOut, SLAPolicyUpdate, TaskSLAOut

router = APIRouter(prefix="/sla-policies", tags=["sla"])


@router.get("/", response_model=list[SLAPolicyOut])
def list_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    configured = {p.priority: p for p in get_policies(db)}
    return [
        configured.get(priority) or SLAPolicyOut(priority=priority, target_hours=hours)
        for priority, hours in DEFAULT_TARGET_HOURS.items()
    ]


@router.put("/{priority}", response_model=SLAPolicyOut)
def update_policy(
    priority: TaskPriority,
    policy_in: SLAPolicyUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return upsert_policy(db, priority, policy_in.target_hours)


sla_task_router = APIRouter(prefix="/tasks/{task_id}/sla", tags=["sla"])


@sla_task_router.get("/", response_model=TaskSLAOut)
def get_task_sla(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada")
    return TaskSLAOut(status=sla_status(db, task), deadline=sla_deadline(db, task))
