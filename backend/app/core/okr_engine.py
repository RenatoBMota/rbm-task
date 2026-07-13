import calendar
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.okr import (
    Objective, KeyResult, KeyResultCheckIn, Initiative, OkrTask, OkrAction, KRDirection, KRCadence,
)
from app.core.timezone import BUSINESS_TZ, aware as _aware, start_of_day as _start_of_day

CADENCE_DAYS: dict[KRCadence, int] = {
    KRCadence.WEEKLY: 7,
    KRCadence.BIWEEKLY: 14,
    KRCadence.MONTHLY: 30,
}

STAGNATION_ALERT_PERIODS = 3
INITIATIVE_STALE_DAYS = 14


def action_progress(action: OkrAction) -> float:
    return 100.0 if action.is_completed else 0.0


def task_progress(task: OkrTask) -> float:
    if task.actions:
        total_weight = sum(a.weight_percent for a in task.actions)
        if total_weight <= 0:
            return 100.0 if task.is_completed else 0.0
        return round(sum(a.weight_percent * action_progress(a) for a in task.actions) / total_weight, 1)
    return 100.0 if task.is_completed else 0.0


def initiative_task_rollup(initiative: Initiative) -> float:
    if initiative.tasks:
        total_weight = sum(t.weight_percent for t in initiative.tasks)
        if total_weight <= 0:
            return 100.0 if initiative.is_completed else 0.0
        return round(sum(t.weight_percent * task_progress(t) for t in initiative.tasks) / total_weight, 1)
    return 100.0 if initiative.is_completed else 0.0


def kr_initiatives_rollup(kr: KeyResult) -> float:
    if not kr.initiatives:
        return 0.0
    total_weight = sum(i.weight_percent for i in kr.initiatives)
    if total_weight <= 0:
        return 0.0
    return round(sum(i.weight_percent * initiative_task_rollup(i) for i in kr.initiatives) / total_weight, 1)


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def kr_indicator_progress(kr: KeyResult) -> float | None:
    if not kr.checkins:
        return None
    latest = kr.checkins[-1].value
    baseline = float(kr.baseline_value)
    target = float(kr.target_value)
    span = target - baseline
    if span == 0:
        return 100.0 if latest == target else 0.0
    if kr.direction == KRDirection.DECREASE:
        span = baseline - target
        progress = (baseline - latest) / span * 100 if span != 0 else 0.0
    else:
        progress = (latest - baseline) / span * 100
    return round(_clamp(progress), 1)


def kr_overall_progress(kr: KeyResult) -> float:
    indicator = kr_indicator_progress(kr)
    if indicator is not None:
        return indicator
    return kr_initiatives_rollup(kr)


def _linear_regression(values: list[float]) -> tuple[float, float]:
    n = len(values)
    if n < 2:
        return 0.0, values[0] if values else 0.0
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values))
    den = sum((x - mean_x) ** 2 for x in xs)
    slope = num / den if den != 0 else 0.0
    intercept = mean_y - slope * mean_x
    return slope, intercept


def _trend(kr: KeyResult, values: list[float]) -> tuple[str, str]:
    if len(values) < 2:
        return "flat", "stable"
    slope, _ = _linear_regression(values[-6:])
    if abs(slope) < 1e-9:
        direction = "flat"
    else:
        direction = "up" if slope > 0 else "down"

    if direction == "flat":
        label = "stable"
    elif kr.direction == KRDirection.DECREASE:
        label = "positive" if direction == "down" else "negative"
    else:
        label = "positive" if direction == "up" else "negative"
    return direction, label


def _forecast(kr: KeyResult, values: list[float], objective_end: datetime) -> tuple[float | None, bool | None]:
    if len(values) < 2:
        return None, None
    slope, intercept = _linear_regression(values)
    latest_checkin = kr.checkins[-1]
    period_days = CADENCE_DAYS.get(kr.cadence, 7)
    remaining_days = (_aware(objective_end) - _aware(latest_checkin.period_end)).days
    periods_remaining = max(remaining_days, 0) / period_days
    forecast_value = slope * (len(values) - 1 + periods_remaining) + intercept
    target = float(kr.target_value)
    if kr.direction == KRDirection.DECREASE:
        hits_target = forecast_value <= target
    else:
        hits_target = forecast_value >= target
    return round(forecast_value, 2), hits_target


def build_kr_detail(db: Session, kr: KeyResult, objective: Objective) -> dict:
    checkins = list(kr.checkins)
    values = [float(c.value) for c in checkins]

    current_value = values[-1] if values else None
    previous_value = values[-2] if len(values) >= 2 else None
    variation_abs = round(current_value - previous_value, 4) if previous_value is not None else None
    variation_pct = (
        round((current_value - previous_value) / abs(previous_value) * 100, 2)
        if previous_value not in (None, 0)
        else None
    )
    average_to_date = round(sum(values) / len(values), 4) if values else None
    best_value = None
    worst_value = None
    if values:
        if kr.direction == KRDirection.DECREASE:
            best_value, worst_value = min(values), max(values)
        else:
            best_value, worst_value = max(values), min(values)
    gap_to_target = round(current_value - float(kr.target_value), 4) if current_value is not None else None

    trend_direction, trend_label = _trend(kr, values)
    forecast_value, forecast_hits_target = _forecast(kr, values, objective.end_date)
    progress_percent = kr_overall_progress(kr)

    history = [
        {
            "period_label": c.period_end.strftime("%d/%m"),
            "value": float(c.value),
            "target": float(kr.target_value),
        }
        for c in checkins
    ]

    initiatives = [
        {
            "id": i.id,
            "title": i.title,
            "weight_percent": float(i.weight_percent),
            "progress_percent": initiative_task_rollup(i),
            "contribution_percent": round(float(i.weight_percent) * initiative_task_rollup(i) / 100, 1),
            "is_completed": i.is_completed,
            "task_count": len(i.tasks),
        }
        for i in kr.initiatives
    ]

    return {
        "id": kr.id,
        "objective_id": kr.objective_id,
        "code": kr.code,
        "title": kr.title,
        "indicator_type": kr.indicator_type,
        "direction": kr.direction,
        "cadence": kr.cadence,
        "baseline_value": float(kr.baseline_value),
        "target_value": float(kr.target_value),
        "owner_id": kr.owner_id,
        "current_value": current_value,
        "previous_value": previous_value,
        "variation_abs": variation_abs,
        "variation_pct": variation_pct,
        "average_to_date": average_to_date,
        "best_value": best_value,
        "worst_value": worst_value,
        "gap_to_target": gap_to_target,
        "progress_percent": progress_percent,
        "trend_direction": trend_direction,
        "trend_label": trend_label,
        "forecast_value": forecast_value,
        "forecast_hits_target": forecast_hits_target,
        "score": progress_percent,
        "history": history,
        "initiatives": initiatives,
        "initiatives_rollup_percent": kr_initiatives_rollup(kr),
    }


def build_initiative_detail(initiative: Initiative) -> dict:
    return {
        "id": initiative.id,
        "key_result_id": initiative.key_result_id,
        "title": initiative.title,
        "weight_percent": initiative.weight_percent,
        "owner_id": initiative.owner_id,
        "is_completed": initiative.is_completed,
        "progress_percent": initiative_task_rollup(initiative),
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "weight_percent": task.weight_percent,
                "owner_id": task.owner_id,
                "due_date": task.due_date,
                "is_completed": task.is_completed,
                "progress_percent": task_progress(task),
                "actions": [
                    {
                        "id": action.id,
                        "title": action.title,
                        "weight_percent": action.weight_percent,
                        "owner_id": action.owner_id,
                        "due_date": action.due_date,
                        "is_completed": action.is_completed,
                        "progress_percent": action_progress(action),
                    }
                    for action in task.actions
                ],
            }
            for task in initiative.tasks
        ],
    }


def build_objective_detail(db: Session, objective: Objective) -> dict:
    key_results = objective.key_results
    kr_summaries = []
    for kr in key_results:
        values = [float(c.value) for c in kr.checkins]
        trend_direction, _ = _trend(kr, values)
        kr_summaries.append({
            "id": kr.id,
            "code": kr.code,
            "title": kr.title,
            "indicator_type": kr.indicator_type,
            "direction": kr.direction,
            "current_value": values[-1] if values else None,
            "target_value": float(kr.target_value),
            "progress_percent": kr_overall_progress(kr),
            "trend_direction": trend_direction,
        })

    performance_percent = (
        round(sum(k["progress_percent"] for k in kr_summaries) / len(kr_summaries), 1)
        if kr_summaries
        else 0.0
    )

    return {
        "id": objective.id,
        "title": objective.title,
        "description": objective.description,
        "start_date": objective.start_date,
        "end_date": objective.end_date,
        "owner_id": objective.owner_id,
        "performance_percent": performance_percent,
        "key_results": kr_summaries,
    }


def build_executive_summary(db: Session, workspace_id: int) -> dict:
    objectives = db.query(Objective).filter(Objective.workspace_id == workspace_id).all()
    now = datetime.now(timezone.utc)

    key_results: list[KeyResult] = []
    initiatives: list[Initiative] = []
    tasks: list[OkrTask] = []
    actions: list[OkrAction] = []
    for obj in objectives:
        key_results.extend(obj.key_results)
    for kr in key_results:
        initiatives.extend(kr.initiatives)
    for initiative in initiatives:
        tasks.extend(initiative.tasks)
    for task in tasks:
        actions.extend(task.actions)

    overall_performance = (
        round(sum(kr_overall_progress(kr) for kr in key_results) / len(key_results), 1)
        if key_results
        else 0.0
    )

    expected_values = []
    for obj in objectives:
        start = _aware(obj.start_date)
        end = _aware(obj.end_date)
        span = (end - start).total_seconds()
        if span > 0:
            elapsed = (now - start).total_seconds()
            expected_values.append(_clamp(elapsed / span * 100))
    expected_performance = round(sum(expected_values) / len(expected_values), 1) if expected_values else 0.0

    leaf_items = tasks + actions
    total_leaf = len(leaf_items)
    completed_leaf = sum(1 for item in leaf_items if item.is_completed)
    overdue_count = sum(
        1 for item in leaf_items
        if item.due_date and not item.is_completed and _aware(item.due_date) < now
    )
    completed_percent = round(completed_leaf / total_leaf * 100, 1) if total_leaf else 0.0
    on_time_percent = round((total_leaf - overdue_count) / total_leaf * 100, 1) if total_leaf else 100.0

    return {
        "objectives_count": len(objectives),
        "key_results_count": len(key_results),
        "initiatives_count": len(initiatives),
        "tasks_count": len(tasks),
        "actions_count": len(actions),
        "overall_performance_percent": overall_performance,
        "expected_performance_percent": expected_performance,
        "overdue_count": overdue_count,
        "on_time_percent": on_time_percent,
        "completed_percent": completed_percent,
    }


def _current_cadence_bounds(cadence: KRCadence, now: datetime, anchor: datetime) -> tuple[datetime, datetime]:
    now = now.astimezone(BUSINESS_TZ)
    anchor = _aware(anchor).astimezone(BUSINESS_TZ)

    if cadence == KRCadence.WEEKLY:
        start = _start_of_day(now) - timedelta(days=(now.weekday() + 1) % 7)
        end = start + timedelta(days=7) - timedelta(microseconds=1)
    elif cadence == KRCadence.MONTHLY:
        start = _start_of_day(now).replace(day=1)
        last_day = calendar.monthrange(start.year, start.month)[1]
        end = start.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
    else:
        anchor_day = _start_of_day(anchor)
        days_elapsed = max((_start_of_day(now) - anchor_day).days, 0)
        period_index = days_elapsed // 14
        start = anchor_day + timedelta(days=period_index * 14)
        end = start + timedelta(days=14) - timedelta(microseconds=1)
    return start, end


def compute_okr_alerts(db: Session, workspace_id: int) -> list[dict]:
    alerts: list[dict] = []
    now = datetime.now(timezone.utc)
    objectives = db.query(Objective).filter(Objective.workspace_id == workspace_id).all()

    for objective in objectives:
        for kr in objective.key_results:
            values = [float(c.value) for c in kr.checkins]
            target = float(kr.target_value)

            if kr.owner_id is None:
                alerts.append({
                    "level": "warning", "entity_type": "key_result", "entity_id": kr.id,
                    "entity_title": f"{kr.code} — {kr.title}",
                    "message": "KR sem responsável definido.",
                })

            if values:
                latest = values[-1]
                below_target = (
                    latest > target if kr.direction == KRDirection.DECREASE else latest < target
                )
                if below_target:
                    alerts.append({
                        "level": "warning", "entity_type": "key_result", "entity_id": kr.id,
                        "entity_title": f"{kr.code} — {kr.title}",
                        "message": "KR abaixo da meta.",
                    })

            if len(values) >= STAGNATION_ALERT_PERIODS:
                recent = values[-STAGNATION_ALERT_PERIODS:]
                stagnant = all(
                    (recent[i + 1] >= recent[i] if kr.direction == KRDirection.DECREASE else recent[i + 1] <= recent[i])
                    for i in range(len(recent) - 1)
                )
                if stagnant:
                    alerts.append({
                        "level": "critical", "entity_type": "key_result", "entity_id": kr.id,
                        "entity_title": f"{kr.code} — {kr.title}",
                        "message": f"{STAGNATION_ALERT_PERIODS} períodos consecutivos sem evolução.",
                    })

            _, forecast_hits = _forecast(kr, values, objective.end_date)
            if forecast_hits is False:
                alerts.append({
                    "level": "critical", "entity_type": "key_result", "entity_id": kr.id,
                    "entity_title": f"{kr.code} — {kr.title}",
                    "message": "Tendência indica que a meta não será atingida no prazo.",
                })

            period_start, period_end = _current_cadence_bounds(kr.cadence, now, objective.start_date)
            has_current_checkin = any(
                period_start <= _aware(c.period_end) <= period_end for c in kr.checkins
            )
            if not has_current_checkin:
                alerts.append({
                    "level": "warning", "entity_type": "key_result", "entity_id": kr.id,
                    "entity_title": f"{kr.code} — {kr.title}",
                    "message": "Sem lançamento no período de cadência atual.",
                })

            if kr.initiatives:
                total_weight = sum(i.weight_percent for i in kr.initiatives)
                if abs(total_weight - 100) > 0.01:
                    alerts.append({
                        "level": "warning", "entity_type": "key_result", "entity_id": kr.id,
                        "entity_title": f"{kr.code} — {kr.title}",
                        "message": f"Soma dos pesos das iniciativas é {total_weight:.0f}%, deveria ser 100%.",
                    })

            for initiative in kr.initiatives:
                if not initiative.is_completed and _aware(initiative.updated_at) < now - timedelta(days=INITIATIVE_STALE_DAYS):
                    alerts.append({
                        "level": "warning", "entity_type": "initiative", "entity_id": initiative.id,
                        "entity_title": initiative.title,
                        "message": f"Sem atualização há mais de {INITIATIVE_STALE_DAYS} dias.",
                    })
                for task in initiative.tasks:
                    if task.due_date and not task.is_completed and _aware(task.due_date) < now:
                        alerts.append({
                            "level": "critical", "entity_type": "task", "entity_id": task.id,
                            "entity_title": task.title,
                            "message": "Tarefa atrasada.",
                        })
                    for action in task.actions:
                        if action.due_date and not action.is_completed and _aware(action.due_date) < now:
                            alerts.append({
                                "level": "critical", "entity_type": "action", "entity_id": action.id,
                                "entity_title": action.title,
                                "message": "Ação vencida.",
                            })

    return alerts
