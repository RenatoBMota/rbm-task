from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.api.access import require_workspace_member
from app.crud.workspace import get_member
from app.crud import okr as crud
from app.core.okr_engine import (
    build_kr_detail, build_objective_detail, build_executive_summary, compute_okr_alerts, build_initiative_detail,
)
from app.models.user import User
from app.models.okr import Objective, KeyResult, Initiative, OkrTask, OkrAction
from app.schemas.okr import (
    ObjectiveCreate, ObjectiveUpdate, ObjectiveOut, ObjectiveDetailOut,
    KeyResultCreate, KeyResultUpdate, KeyResultOut, KeyResultDetailOut,
    CheckInCreate, CheckInOut,
    InitiativeCreate, InitiativeUpdate, InitiativeOut,
    OkrTaskCreate, OkrTaskUpdate, OkrTaskOut,
    OkrActionCreate, OkrActionUpdate, OkrActionOut,
    ExecutiveSummaryOut, OkrAlertOut, InitiativeDetailOut,
)

router = APIRouter(prefix="/okr", tags=["okr"])


def _get_objective_or_404(db: Session, objective_id: int, user_id: int) -> Objective:
    objective = crud.get_objective(db, objective_id)
    if not objective or not get_member(db, objective.workspace_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Objetivo não encontrado")
    return objective


def _get_kr_or_404(db: Session, kr_id: int, user_id: int) -> KeyResult:
    kr = crud.get_key_result(db, kr_id)
    if not kr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KR não encontrado")
    _get_objective_or_404(db, kr.objective_id, user_id)
    return kr


def _get_initiative_or_404(db: Session, initiative_id: int, user_id: int) -> Initiative:
    initiative = crud.get_initiative(db, initiative_id)
    if not initiative:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Iniciativa não encontrada")
    _get_kr_or_404(db, initiative.key_result_id, user_id)
    return initiative


def _get_okr_task_or_404(db: Session, task_id: int, user_id: int) -> OkrTask:
    task = crud.get_okr_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada")
    _get_initiative_or_404(db, task.initiative_id, user_id)
    return task


def _get_okr_action_or_404(db: Session, action_id: int, user_id: int) -> OkrAction:
    action = crud.get_okr_action(db, action_id)
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ação não encontrada")
    _get_okr_task_or_404(db, action.task_id, user_id)
    return action


@router.get("/objectives", response_model=list[ObjectiveOut])
def list_objectives(
    workspace_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    require_workspace_member(db, workspace_id, current_user.id)
    return crud.get_objectives(db, workspace_id)


@router.post("/objectives", response_model=ObjectiveOut, status_code=status.HTTP_201_CREATED)
def create_objective(
    workspace_id: int, objective_in: ObjectiveCreate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    require_workspace_member(db, workspace_id, current_user.id)
    return crud.create_objective(db, objective_in, workspace_id)


@router.get("/objectives/{objective_id}", response_model=ObjectiveDetailOut)
def get_objective_detail(
    objective_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    objective = _get_objective_or_404(db, objective_id, current_user.id)
    return build_objective_detail(db, objective)


@router.put("/objectives/{objective_id}", response_model=ObjectiveOut)
def update_objective(
    objective_id: int, objective_in: ObjectiveUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    objective = _get_objective_or_404(db, objective_id, current_user.id)
    return crud.update_objective(db, objective, objective_in)


@router.delete("/objectives/{objective_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_objective(
    objective_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    objective = _get_objective_or_404(db, objective_id, current_user.id)
    crud.delete_objective(db, objective)


@router.post("/objectives/{objective_id}/key-results", response_model=KeyResultOut, status_code=status.HTTP_201_CREATED)
def create_key_result(
    objective_id: int, kr_in: KeyResultCreate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    _get_objective_or_404(db, objective_id, current_user.id)
    return crud.create_key_result(db, kr_in, objective_id)


@router.get("/key-results/{kr_id}", response_model=KeyResultDetailOut)
def get_key_result_detail(
    kr_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    kr = _get_kr_or_404(db, kr_id, current_user.id)
    return build_kr_detail(db, kr, kr.objective)


@router.put("/key-results/{kr_id}", response_model=KeyResultOut)
def update_key_result(
    kr_id: int, kr_in: KeyResultUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    kr = _get_kr_or_404(db, kr_id, current_user.id)
    return crud.update_key_result(db, kr, kr_in)


@router.delete("/key-results/{kr_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_key_result(
    kr_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    kr = _get_kr_or_404(db, kr_id, current_user.id)
    crud.delete_key_result(db, kr)


@router.post("/key-results/{kr_id}/checkins", response_model=CheckInOut, status_code=status.HTTP_201_CREATED)
def create_checkin(
    kr_id: int, checkin_in: CheckInCreate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    _get_kr_or_404(db, kr_id, current_user.id)
    if checkin_in.period_end < checkin_in.period_start:
        raise HTTPException(status_code=400, detail="O fim do período não pode ser anterior ao início.")
    return crud.create_checkin(db, checkin_in, kr_id, current_user.id)


@router.post("/key-results/{kr_id}/initiatives", response_model=InitiativeOut, status_code=status.HTTP_201_CREATED)
def create_initiative(
    kr_id: int, initiative_in: InitiativeCreate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    _get_kr_or_404(db, kr_id, current_user.id)
    return crud.create_initiative(db, initiative_in, kr_id)


@router.get("/initiatives/{initiative_id}", response_model=InitiativeDetailOut)
def get_initiative_detail(
    initiative_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    initiative = _get_initiative_or_404(db, initiative_id, current_user.id)
    return build_initiative_detail(initiative)


@router.put("/initiatives/{initiative_id}", response_model=InitiativeOut)
def update_initiative(
    initiative_id: int, initiative_in: InitiativeUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    initiative = _get_initiative_or_404(db, initiative_id, current_user.id)
    return crud.update_initiative(db, initiative, initiative_in)


@router.delete("/initiatives/{initiative_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_initiative(
    initiative_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    initiative = _get_initiative_or_404(db, initiative_id, current_user.id)
    crud.delete_initiative(db, initiative)


@router.post("/initiatives/{initiative_id}/tasks", response_model=OkrTaskOut, status_code=status.HTTP_201_CREATED)
def create_okr_task(
    initiative_id: int, task_in: OkrTaskCreate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    _get_initiative_or_404(db, initiative_id, current_user.id)
    return crud.create_okr_task(db, task_in, initiative_id)


@router.put("/tasks/{task_id}", response_model=OkrTaskOut)
def update_okr_task(
    task_id: int, task_in: OkrTaskUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    task = _get_okr_task_or_404(db, task_id, current_user.id)
    return crud.update_okr_task(db, task, task_in)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_okr_task(
    task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    task = _get_okr_task_or_404(db, task_id, current_user.id)
    crud.delete_okr_task(db, task)


@router.post("/tasks/{task_id}/actions", response_model=OkrActionOut, status_code=status.HTTP_201_CREATED)
def create_okr_action(
    task_id: int, action_in: OkrActionCreate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    _get_okr_task_or_404(db, task_id, current_user.id)
    return crud.create_okr_action(db, action_in, task_id)


@router.put("/actions/{action_id}", response_model=OkrActionOut)
def update_okr_action(
    action_id: int, action_in: OkrActionUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    action = _get_okr_action_or_404(db, action_id, current_user.id)
    return crud.update_okr_action(db, action, action_in)


@router.delete("/actions/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_okr_action(
    action_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    action = _get_okr_action_or_404(db, action_id, current_user.id)
    crud.delete_okr_action(db, action)


@router.get("/workspaces/{workspace_id}/executive-summary", response_model=ExecutiveSummaryOut)
def executive_summary(
    workspace_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    require_workspace_member(db, workspace_id, current_user.id)
    return build_executive_summary(db, workspace_id)


@router.get("/workspaces/{workspace_id}/alerts", response_model=list[OkrAlertOut])
def alerts(
    workspace_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    require_workspace_member(db, workspace_id, current_user.id)
    return compute_okr_alerts(db, workspace_id)
