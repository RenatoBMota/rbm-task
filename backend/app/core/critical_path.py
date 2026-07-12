from collections import defaultdict, deque
from app.models.task import Task
from app.models.task_dependency import TaskDependency, DependencyType


def _task_duration_days(task: Task) -> int:
    if task.is_milestone:
        return 0
    if task.start_date and task.due_date:
        return max((task.due_date - task.start_date).days, 0)
    return 0


def compute_critical_path(tasks: list[Task], dependencies: list[TaskDependency]) -> set[int]:
    schedulable_ids = {t.id for t in tasks if t.is_milestone or (t.start_date and t.due_date)}
    if not schedulable_ids:
        return set()

    durations = {t.id: _task_duration_days(t) for t in tasks if t.id in schedulable_ids}

    successors: dict[int, list[tuple[int, TaskDependency]]] = defaultdict(list)
    predecessors: dict[int, list[tuple[int, TaskDependency]]] = defaultdict(list)
    in_degree: dict[int, int] = defaultdict(int)
    for dep in dependencies:
        if dep.task_id not in schedulable_ids or dep.depends_on_id not in schedulable_ids:
            continue
        successors[dep.depends_on_id].append((dep.task_id, dep))
        predecessors[dep.task_id].append((dep.depends_on_id, dep))
        in_degree[dep.task_id] += 1

    queue = deque([tid for tid in schedulable_ids if in_degree[tid] == 0])
    order: list[int] = []
    indegree_remaining = dict(in_degree)
    while queue:
        node = queue.popleft()
        order.append(node)
        for succ_id, _ in successors[node]:
            indegree_remaining[succ_id] -= 1
            if indegree_remaining[succ_id] == 0:
                queue.append(succ_id)

    if len(order) != len(schedulable_ids):
        # dependency cycle — cannot compute a meaningful critical path
        return set()

    earliest_start: dict[int, int] = {}
    earliest_finish: dict[int, int] = {}
    for task_id in order:
        duration = durations[task_id]
        preds = predecessors[task_id]
        if not preds:
            es = 0
        else:
            es = 0
            for pred_id, dep in preds:
                lag = dep.lag_days
                if dep.dependency_type == DependencyType.FINISH_START:
                    constraint = earliest_finish[pred_id] + lag
                elif dep.dependency_type == DependencyType.START_START:
                    constraint = earliest_start[pred_id] + lag
                elif dep.dependency_type == DependencyType.FINISH_FINISH:
                    constraint = earliest_finish[pred_id] + lag - duration
                else:  # START_FINISH
                    constraint = earliest_start[pred_id] + lag - duration
                es = max(es, constraint)
        earliest_start[task_id] = es
        earliest_finish[task_id] = es + duration

    project_end = max(earliest_finish.values())

    latest_finish: dict[int, int] = {}
    latest_start: dict[int, int] = {}
    for task_id in reversed(order):
        duration = durations[task_id]
        succs = successors[task_id]
        if not succs:
            lf = project_end
        else:
            lf = project_end
            for succ_id, dep in succs:
                lag = dep.lag_days
                if dep.dependency_type == DependencyType.FINISH_START:
                    constraint = latest_start[succ_id] - lag
                elif dep.dependency_type == DependencyType.START_START:
                    constraint = latest_start[succ_id] - lag + duration
                elif dep.dependency_type == DependencyType.FINISH_FINISH:
                    constraint = latest_finish[succ_id] - lag
                else:  # START_FINISH
                    constraint = latest_finish[succ_id] - lag + duration
                lf = min(lf, constraint)
        latest_finish[task_id] = lf
        latest_start[task_id] = lf - duration

    return {tid for tid in order if (latest_start[tid] - earliest_start[tid]) == 0}
