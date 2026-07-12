from datetime import datetime
from typing import Any
from pydantic import BaseModel
from app.models.automation import TriggerEvent


class AutomationRuleBase(BaseModel):
    name: str
    trigger_event: TriggerEvent
    conditions: dict[str, Any] = {}
    actions: list[dict[str, Any]] = []
    project_id: int | None = None
    is_active: bool = True


class AutomationRuleCreate(AutomationRuleBase):
    pass


class AutomationRuleUpdate(BaseModel):
    name: str | None = None
    trigger_event: TriggerEvent | None = None
    conditions: dict[str, Any] | None = None
    actions: list[dict[str, Any]] | None = None
    project_id: int | None = None
    is_active: bool | None = None


class AutomationRuleOut(AutomationRuleBase):
    id: int
    created_by_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AutomationLogOut(BaseModel):
    id: int
    task_id: int | None
    success: bool
    detail: str | None
    executed_at: datetime

    model_config = {"from_attributes": True}
