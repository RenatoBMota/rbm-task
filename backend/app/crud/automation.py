from sqlalchemy.orm import Session
from app.models.automation import AutomationRule, AutomationLog
from app.schemas.automation import AutomationRuleCreate, AutomationRuleUpdate


def get_rule(db: Session, rule_id: int) -> AutomationRule | None:
    return db.query(AutomationRule).filter(AutomationRule.id == rule_id).first()


def get_rules(db: Session) -> list[AutomationRule]:
    return db.query(AutomationRule).order_by(AutomationRule.created_at.desc()).all()


def create_rule(db: Session, rule_in: AutomationRuleCreate, created_by_id: int) -> AutomationRule:
    rule = AutomationRule(**rule_in.model_dump(), created_by_id=created_by_id)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_rule(db: Session, rule: AutomationRule, rule_in: AutomationRuleUpdate) -> AutomationRule:
    update_data = rule_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, rule: AutomationRule) -> None:
    db.delete(rule)
    db.commit()


def get_logs(db: Session, rule_id: int) -> list[AutomationLog]:
    return (
        db.query(AutomationLog)
        .filter(AutomationLog.rule_id == rule_id)
        .order_by(AutomationLog.executed_at.desc())
        .limit(50)
        .all()
    )
