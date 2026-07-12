from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_admin
from app.crud.automation import get_rule, get_rules, create_rule, update_rule, delete_rule, get_logs
from app.models.user import User
from app.schemas.automation import (
    AutomationRuleCreate, AutomationRuleUpdate, AutomationRuleOut, AutomationLogOut,
)

router = APIRouter(prefix="/automations", tags=["automations"])


@router.get("/", response_model=list[AutomationRuleOut])
def list_rules(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return get_rules(db)


@router.post("/", response_model=AutomationRuleOut, status_code=status.HTTP_201_CREATED)
def create(
    rule_in: AutomationRuleCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return create_rule(db, rule_in, created_by_id=admin.id)


@router.put("/{rule_id}", response_model=AutomationRuleOut)
def update(
    rule_id: int,
    rule_in: AutomationRuleUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    rule = get_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automação não encontrada")
    return update_rule(db, rule, rule_in)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    rule_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    rule = get_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automação não encontrada")
    delete_rule(db, rule)


@router.get("/{rule_id}/logs", response_model=list[AutomationLogOut])
def list_logs(
    rule_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    if not get_rule(db, rule_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automação não encontrada")
    return get_logs(db, rule_id)
