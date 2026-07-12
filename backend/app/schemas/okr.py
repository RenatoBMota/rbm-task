from datetime import datetime
from pydantic import BaseModel
from app.models.okr import IndicatorType, KRCadence, KRDirection


class ObjectiveCreate(BaseModel):
    title: str
    description: str | None = None
    start_date: datetime
    end_date: datetime
    owner_id: int | None = None


class ObjectiveUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    owner_id: int | None = None


class ObjectiveOut(BaseModel):
    id: int
    workspace_id: int
    title: str
    description: str | None
    start_date: datetime
    end_date: datetime
    owner_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class KeyResultCreate(BaseModel):
    code: str
    title: str
    indicator_type: IndicatorType = IndicatorType.QUANTITY
    direction: KRDirection = KRDirection.INCREASE
    cadence: KRCadence = KRCadence.WEEKLY
    baseline_value: float = 0
    target_value: float
    owner_id: int | None = None


class KeyResultUpdate(BaseModel):
    code: str | None = None
    title: str | None = None
    indicator_type: IndicatorType | None = None
    direction: KRDirection | None = None
    cadence: KRCadence | None = None
    baseline_value: float | None = None
    target_value: float | None = None
    owner_id: int | None = None


class KeyResultOut(BaseModel):
    id: int
    objective_id: int
    code: str
    title: str
    indicator_type: IndicatorType
    direction: KRDirection
    cadence: KRCadence
    baseline_value: float
    target_value: float
    owner_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CheckInCreate(BaseModel):
    period_start: datetime
    period_end: datetime
    value: float
    comment: str | None = None


class CheckInOut(BaseModel):
    id: int
    key_result_id: int
    period_start: datetime
    period_end: datetime
    value: float
    comment: str | None
    created_by_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InitiativeCreate(BaseModel):
    title: str
    weight_percent: float = 0
    owner_id: int | None = None
    is_completed: bool = False


class InitiativeUpdate(BaseModel):
    title: str | None = None
    weight_percent: float | None = None
    owner_id: int | None = None
    is_completed: bool | None = None


class InitiativeOut(BaseModel):
    id: int
    key_result_id: int
    title: str
    weight_percent: float
    owner_id: int | None
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OkrTaskCreate(BaseModel):
    title: str
    weight_percent: float = 0
    owner_id: int | None = None
    due_date: datetime | None = None
    is_completed: bool = False


class OkrTaskUpdate(BaseModel):
    title: str | None = None
    weight_percent: float | None = None
    owner_id: int | None = None
    due_date: datetime | None = None
    is_completed: bool | None = None


class OkrTaskOut(BaseModel):
    id: int
    initiative_id: int
    title: str
    weight_percent: float
    owner_id: int | None
    due_date: datetime | None
    is_completed: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


class OkrActionCreate(BaseModel):
    title: str
    weight_percent: float = 0
    owner_id: int | None = None
    due_date: datetime | None = None
    is_completed: bool = False


class OkrActionUpdate(BaseModel):
    title: str | None = None
    weight_percent: float | None = None
    owner_id: int | None = None
    due_date: datetime | None = None
    is_completed: bool | None = None


class OkrActionOut(BaseModel):
    id: int
    task_id: int
    title: str
    weight_percent: float
    owner_id: int | None
    due_date: datetime | None
    is_completed: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


class OkrActionDetailOut(BaseModel):
    id: int
    title: str
    weight_percent: float
    owner_id: int | None
    due_date: datetime | None
    is_completed: bool
    progress_percent: float


class OkrTaskDetailOut(BaseModel):
    id: int
    title: str
    weight_percent: float
    owner_id: int | None
    due_date: datetime | None
    is_completed: bool
    progress_percent: float
    actions: list[OkrActionDetailOut]


class InitiativeDetailOut(BaseModel):
    id: int
    key_result_id: int
    title: str
    weight_percent: float
    owner_id: int | None
    is_completed: bool
    progress_percent: float
    tasks: list[OkrTaskDetailOut]


class KRHistoryPoint(BaseModel):
    period_label: str
    value: float
    target: float


class InitiativeSummaryOut(BaseModel):
    id: int
    title: str
    weight_percent: float
    progress_percent: float
    contribution_percent: float
    is_completed: bool
    task_count: int


class KeyResultDetailOut(BaseModel):
    id: int
    objective_id: int
    code: str
    title: str
    indicator_type: IndicatorType
    direction: KRDirection
    cadence: KRCadence
    baseline_value: float
    target_value: float
    owner_id: int | None
    current_value: float | None
    previous_value: float | None
    variation_abs: float | None
    variation_pct: float | None
    average_to_date: float | None
    best_value: float | None
    worst_value: float | None
    gap_to_target: float | None
    progress_percent: float
    trend_direction: str
    trend_label: str
    forecast_value: float | None
    forecast_hits_target: bool | None
    score: float
    history: list[KRHistoryPoint]
    initiatives: list[InitiativeSummaryOut]
    initiatives_rollup_percent: float


class KeyResultSummaryOut(BaseModel):
    id: int
    code: str
    title: str
    indicator_type: IndicatorType
    direction: KRDirection
    current_value: float | None
    target_value: float
    progress_percent: float
    trend_direction: str


class ObjectiveDetailOut(BaseModel):
    id: int
    title: str
    description: str | None
    start_date: datetime
    end_date: datetime
    owner_id: int | None
    performance_percent: float
    key_results: list[KeyResultSummaryOut]


class ExecutiveSummaryOut(BaseModel):
    objectives_count: int
    key_results_count: int
    initiatives_count: int
    tasks_count: int
    actions_count: int
    overall_performance_percent: float
    expected_performance_percent: float
    overdue_count: int
    on_time_percent: float
    completed_percent: float


class OkrAlertOut(BaseModel):
    level: str
    entity_type: str
    entity_id: int
    entity_title: str
    message: str
