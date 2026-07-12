from sqlalchemy.orm import Session
from app.models.okr import Objective, KeyResult, KeyResultCheckIn, Initiative, OkrTask, OkrAction
from app.schemas.okr import (
    ObjectiveCreate, ObjectiveUpdate, KeyResultCreate, KeyResultUpdate, CheckInCreate,
    InitiativeCreate, InitiativeUpdate, OkrTaskCreate, OkrTaskUpdate, OkrActionCreate, OkrActionUpdate,
)


def get_objective(db: Session, objective_id: int) -> Objective | None:
    return db.query(Objective).filter(Objective.id == objective_id).first()


def get_objectives(db: Session, workspace_id: int) -> list[Objective]:
    return db.query(Objective).filter(Objective.workspace_id == workspace_id).order_by(Objective.created_at).all()


def create_objective(db: Session, objective_in: ObjectiveCreate, workspace_id: int) -> Objective:
    objective = Objective(**objective_in.model_dump(), workspace_id=workspace_id)
    db.add(objective)
    db.commit()
    db.refresh(objective)
    return objective


def update_objective(db: Session, objective: Objective, objective_in: ObjectiveUpdate) -> Objective:
    for field, value in objective_in.model_dump(exclude_unset=True).items():
        setattr(objective, field, value)
    db.commit()
    db.refresh(objective)
    return objective


def delete_objective(db: Session, objective: Objective) -> None:
    db.delete(objective)
    db.commit()


def get_key_result(db: Session, key_result_id: int) -> KeyResult | None:
    return db.query(KeyResult).filter(KeyResult.id == key_result_id).first()


def create_key_result(db: Session, kr_in: KeyResultCreate, objective_id: int) -> KeyResult:
    kr = KeyResult(**kr_in.model_dump(), objective_id=objective_id)
    db.add(kr)
    db.commit()
    db.refresh(kr)
    return kr


def update_key_result(db: Session, kr: KeyResult, kr_in: KeyResultUpdate) -> KeyResult:
    for field, value in kr_in.model_dump(exclude_unset=True).items():
        setattr(kr, field, value)
    db.commit()
    db.refresh(kr)
    return kr


def delete_key_result(db: Session, kr: KeyResult) -> None:
    db.delete(kr)
    db.commit()


def create_checkin(db: Session, checkin_in: CheckInCreate, key_result_id: int, created_by_id: int) -> KeyResultCheckIn:
    checkin = KeyResultCheckIn(**checkin_in.model_dump(), key_result_id=key_result_id, created_by_id=created_by_id)
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return checkin


def get_initiative(db: Session, initiative_id: int) -> Initiative | None:
    return db.query(Initiative).filter(Initiative.id == initiative_id).first()


def create_initiative(db: Session, initiative_in: InitiativeCreate, key_result_id: int) -> Initiative:
    initiative = Initiative(**initiative_in.model_dump(), key_result_id=key_result_id)
    db.add(initiative)
    db.commit()
    db.refresh(initiative)
    return initiative


def update_initiative(db: Session, initiative: Initiative, initiative_in: InitiativeUpdate) -> Initiative:
    for field, value in initiative_in.model_dump(exclude_unset=True).items():
        setattr(initiative, field, value)
    db.commit()
    db.refresh(initiative)
    return initiative


def delete_initiative(db: Session, initiative: Initiative) -> None:
    db.delete(initiative)
    db.commit()


def get_okr_task(db: Session, task_id: int) -> OkrTask | None:
    return db.query(OkrTask).filter(OkrTask.id == task_id).first()


def create_okr_task(db: Session, task_in: OkrTaskCreate, initiative_id: int) -> OkrTask:
    task = OkrTask(**task_in.model_dump(), initiative_id=initiative_id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_okr_task(db: Session, task: OkrTask, task_in: OkrTaskUpdate) -> OkrTask:
    for field, value in task_in.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


def delete_okr_task(db: Session, task: OkrTask) -> None:
    db.delete(task)
    db.commit()


def get_okr_action(db: Session, action_id: int) -> OkrAction | None:
    return db.query(OkrAction).filter(OkrAction.id == action_id).first()


def create_okr_action(db: Session, action_in: OkrActionCreate, task_id: int) -> OkrAction:
    action = OkrAction(**action_in.model_dump(), task_id=task_id)
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def update_okr_action(db: Session, action: OkrAction, action_in: OkrActionUpdate) -> OkrAction:
    for field, value in action_in.model_dump(exclude_unset=True).items():
        setattr(action, field, value)
    db.commit()
    db.refresh(action)
    return action


def delete_okr_action(db: Session, action: OkrAction) -> None:
    db.delete(action)
    db.commit()
