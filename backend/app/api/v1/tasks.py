from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.crud.task import (
    get_task, get_tasks, get_today_tasks, get_overdue_tasks, get_board_tasks, get_subtasks,
    create_task, update_task, delete_task, move_task, duplicate_task
)
from app.crud.task_history import get_history
from app.crud.task_dependency import (
    get_dependency, get_dependencies, add_dependency, update_dependency, remove_dependency,
)
from app.crud.label import get_label, attach_label, detach_label
from app.crud.reminder import get_reminder, get_reminders, create_reminder, delete_reminder
from app.api.access import require_project_member, require_task_access, require_workspace_member
from app.core.exceptions import TaskBlockedError
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskOut, TaskMove, TaskDuplicate
from app.schemas.task_history import TaskHistoryOut
from app.schemas.task_dependency import TaskDependencyCreate, TaskDependencyUpdate, TaskDependencyOut
from app.schemas.reminder import ReminderCreate, ReminderOut

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
def list_tasks(
    project_id: int | None = None,
    workspace_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if project_id:
        require_project_member(db, project_id, current_user.id)
        return get_tasks(db, project_id=project_id, skip=skip, limit=limit)
    if workspace_id:
        require_workspace_member(db, workspace_id, current_user.id)
    return get_tasks(db, assignee_id=current_user.id, workspace_id=workspace_id, skip=skip, limit=limit)


@router.get("/today", response_model=list[TaskOut])
def list_today_tasks(
    workspace_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if workspace_id:
        require_workspace_member(db, workspace_id, current_user.id)
    return get_today_tasks(db, current_user.id, workspace_id=workspace_id)


@router.get("/overdue", response_model=list[TaskOut])
def list_overdue_tasks(
    workspace_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if workspace_id:
        require_workspace_member(db, workspace_id, current_user.id)
    return get_overdue_tasks(db, current_user.id, workspace_id=workspace_id)


@router.get("/board", response_model=list[TaskOut])
def list_board_tasks(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_member(db, project_id, current_user.id)
    return get_board_tasks(db, project_id)


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if task_in.project_id:
        require_project_member(db, task_in.project_id, current_user.id)
    return create_task(db, task_in, creator_id=current_user.id)


@router.get("/{task_id}", response_model=TaskOut)
def get(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return require_task_access(db, task_id, current_user.id)


@router.get("/{task_id}/subtasks", response_model=list[TaskOut])
def list_subtasks(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_task_access(db, task_id, current_user.id)
    return get_subtasks(db, task_id)


@router.put("/{task_id}", response_model=TaskOut)
def update(
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = require_task_access(db, task_id, current_user.id)
    try:
        return update_task(db, task, task_in, changed_by_id=current_user.id)
    except TaskBlockedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/{task_id}/move", response_model=TaskOut)
def move(
    task_id: int,
    move_in: TaskMove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = require_task_access(db, task_id, current_user.id)
    try:
        return move_task(db, task, move_in.status, move_in.position, changed_by_id=current_user.id)
    except TaskBlockedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{task_id}/history", response_model=list[TaskHistoryOut])
def list_history(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_task_access(db, task_id, current_user.id)
    return get_history(db, task_id)


def _dependency_out(dep) -> TaskDependencyOut:
    return TaskDependencyOut(
        id=dep.id,
        task_id=dep.task_id,
        depends_on_id=dep.depends_on_id,
        depends_on_title=dep.depends_on.title,
        depends_on_completed=dep.depends_on.is_completed,
        dependency_type=dep.dependency_type,
        lag_days=dep.lag_days,
        hardness=dep.hardness,
    )


@router.get("/{task_id}/dependencies", response_model=list[TaskDependencyOut])
def list_dependencies(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_task_access(db, task_id, current_user.id)
    return [_dependency_out(dep) for dep in get_dependencies(db, task_id)]


@router.post("/{task_id}/dependencies", response_model=TaskDependencyOut, status_code=status.HTTP_201_CREATED)
def create_dependency(
    task_id: int,
    dependency_in: TaskDependencyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_task_access(db, task_id, current_user.id)
    require_task_access(db, dependency_in.depends_on_id, current_user.id)
    try:
        dependency = add_dependency(
            db,
            task_id,
            dependency_in.depends_on_id,
            dependency_type=dependency_in.dependency_type,
            lag_days=dependency_in.lag_days,
            hardness=dependency_in.hardness,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return _dependency_out(dependency)


@router.put("/{task_id}/dependencies/{dependency_id}", response_model=TaskDependencyOut)
def update_dependency_route(
    task_id: int,
    dependency_id: int,
    dependency_in: TaskDependencyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_task_access(db, task_id, current_user.id)
    dependency = get_dependency(db, dependency_id)
    if not dependency or dependency.task_id != task_id:
        raise HTTPException(status_code=404, detail="Dependência não encontrada")
    dependency = update_dependency(
        db,
        dependency,
        dependency_type=dependency_in.dependency_type,
        lag_days=dependency_in.lag_days,
        hardness=dependency_in.hardness,
    )
    return _dependency_out(dependency)


@router.delete("/{task_id}/dependencies/{dependency_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dependency(
    task_id: int,
    dependency_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_task_access(db, task_id, current_user.id)
    dependency = get_dependency(db, dependency_id)
    if not dependency or dependency.task_id != task_id:
        raise HTTPException(status_code=404, detail="Dependência não encontrada")
    remove_dependency(db, dependency)


@router.post("/{task_id}/duplicate", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def duplicate(
    task_id: int,
    duplicate_in: TaskDuplicate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = require_task_access(db, task_id, current_user.id)
    return duplicate_task(db, task, duplicate_in.title, creator_id=current_user.id)


@router.post("/{task_id}/labels/{label_id}", response_model=TaskOut)
def add_label(
    task_id: int,
    label_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = require_task_access(db, task_id, current_user.id)
    label = get_label(db, label_id, owner_id=current_user.id)
    if not label:
        raise HTTPException(status_code=404, detail="Etiqueta não encontrada")
    return attach_label(db, task, label)


@router.delete("/{task_id}/labels/{label_id}", response_model=TaskOut)
def remove_label(
    task_id: int,
    label_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = require_task_access(db, task_id, current_user.id)
    label = get_label(db, label_id, owner_id=current_user.id)
    if not label:
        raise HTTPException(status_code=404, detail="Etiqueta não encontrada")
    return detach_label(db, task, label)


@router.get("/{task_id}/reminders", response_model=list[ReminderOut])
def list_reminders(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_task_access(db, task_id, current_user.id)
    return get_reminders(db, task_id)


@router.post("/{task_id}/reminders", response_model=ReminderOut, status_code=status.HTTP_201_CREATED)
def create_task_reminder(
    task_id: int,
    reminder_in: ReminderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_task_access(db, task_id, current_user.id)
    return create_reminder(db, task_id, reminder_in.remind_at)


@router.delete("/{task_id}/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task_reminder(
    task_id: int,
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_task_access(db, task_id, current_user.id)
    reminder = get_reminder(db, reminder_id)
    if not reminder or reminder.task_id != task_id:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado")
    delete_reminder(db, reminder)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = require_task_access(db, task_id, current_user.id)
    delete_task(db, task)
