from datetime import datetime, timedelta, timezone
from app.core.critical_path import compute_critical_path
from app.models.task import Task
from app.models.task_dependency import TaskDependency, DependencyType

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _task(task_id: int, duration_days: int, is_milestone: bool = False) -> Task:
    task = Task(id=task_id, is_milestone=is_milestone)
    if not is_milestone:
        task.start_date = BASE
        task.due_date = BASE + timedelta(days=duration_days)
    return task


def _dep(task_id: int, depends_on_id: int, dep_type=DependencyType.FINISH_START, lag: int = 0) -> TaskDependency:
    return TaskDependency(task_id=task_id, depends_on_id=depends_on_id, dependency_type=dep_type, lag_days=lag)


def test_linear_chain_is_fully_critical():
    tasks = [_task(1, 3), _task(2, 2), _task(3, 1)]
    deps = [_dep(2, 1), _dep(3, 2)]

    critical = compute_critical_path(tasks, deps)
    assert critical == {1, 2, 3}


def test_longer_branch_is_critical_shorter_branch_is_not():
    tasks = [_task(1, 1), _task(2, 5), _task(3, 1), _task(4, 1)]
    deps = [_dep(2, 1), _dep(3, 1), _dep(4, 2), _dep(4, 3)]

    critical = compute_critical_path(tasks, deps)
    assert critical == {1, 2, 4}
    assert 3 not in critical


def test_unscheduled_tasks_are_ignored():
    unscheduled = Task(id=2, is_milestone=False)  # no start/due date
    tasks = [_task(1, 2), unscheduled]
    deps = [_dep(2, 1)]

    critical = compute_critical_path(tasks, deps)
    assert critical == {1}


def test_milestone_has_zero_duration():
    tasks = [_task(1, 3), _task(2, 0, is_milestone=True)]
    deps = [_dep(2, 1)]

    critical = compute_critical_path(tasks, deps)
    assert critical == {1, 2}


def test_lag_extends_but_does_not_break_critical_chain():
    tasks = [_task(1, 2), _task(2, 2)]
    deps = [_dep(2, 1, lag=3)]

    critical = compute_critical_path(tasks, deps)
    assert critical == {1, 2}


def test_cycle_returns_empty_set_without_crashing():
    tasks = [_task(1, 2), _task(2, 2)]
    deps = [_dep(2, 1), _dep(1, 2)]

    critical = compute_critical_path(tasks, deps)
    assert critical == set()


def test_no_tasks_returns_empty_set():
    assert compute_critical_path([], []) == set()
