import csv
from io import StringIO
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.crud.project import (
    get_project, get_projects, create_project, update_project, delete_project, duplicate_project,
)
from app.crud.task import get_all_project_tasks
from app.crud.workspace import get_member
from app.crud.resource import task_cost
from app.core.critical_path import compute_critical_path
from app.models.user import User
from app.models.task_dependency import TaskDependency
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut, ProjectDuplicate
from app.schemas.gantt import GanttData, GanttDependency

router = APIRouter(prefix="/projects", tags=["projects"])


def _require_workspace_member(db: Session, workspace_id: int, user_id: int) -> None:
    if not get_member(db, workspace_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Área de trabalho não encontrada")


def _get_project_with_access(db: Session, project_id: int, user_id: int):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    _require_workspace_member(db, project.workspace_id, user_id)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(
    workspace_id: int,
    skip: int = 0,
    limit: int = 100,
    include_archived: bool = False,
    templates_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_workspace_member(db, workspace_id, current_user.id)
    return get_projects(
        db, workspace_id=workspace_id, skip=skip, limit=limit,
        include_archived=include_archived, templates_only=templates_only,
    )


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_workspace_member(db, project_in.workspace_id, current_user.id)
    return create_project(db, project_in, owner_id=current_user.id)


@router.get("/{project_id}", response_model=ProjectOut)
def get(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_project_with_access(db, project_id, current_user.id)


@router.put("/{project_id}", response_model=ProjectOut)
def update(
    project_id: int,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_with_access(db, project_id, current_user.id)
    return update_project(db, project, project_in)


@router.post("/{project_id}/duplicate", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def duplicate(
    project_id: int,
    duplicate_in: ProjectDuplicate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_with_access(db, project_id, current_user.id)
    return duplicate_project(db, project, duplicate_in.name, owner_id=current_user.id)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_with_access(db, project_id, current_user.id)
    delete_project(db, project)


@router.get("/{project_id}/gantt", response_model=GanttData)
def get_gantt(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_with_access(db, project_id, current_user.id)
    tasks = get_all_project_tasks(db, project_id)
    task_ids = [t.id for t in tasks]
    dependencies = (
        db.query(TaskDependency)
        .filter(TaskDependency.task_id.in_(task_ids), TaskDependency.depends_on_id.in_(task_ids))
        .all()
        if task_ids
        else []
    )
    critical_ids = compute_critical_path(tasks, dependencies)
    return GanttData(
        tasks=tasks,
        dependencies=[GanttDependency.model_validate(d) for d in dependencies],
        critical_task_ids=sorted(critical_ids),
        task_costs={t.id: task_cost(t) for t in tasks},
    )


@router.get("/{project_id}/gantt/export.csv")
def export_gantt_csv(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_with_access(db, project_id, current_user.id)
    tasks = get_all_project_tasks(db, project_id)
    task_ids = [t.id for t in tasks]
    dependencies = (
        db.query(TaskDependency)
        .filter(TaskDependency.task_id.in_(task_ids), TaskDependency.depends_on_id.in_(task_ids))
        .all()
        if task_ids
        else []
    )
    critical_ids = compute_critical_path(tasks, dependencies)
    deps_by_task: dict[int, list[str]] = {}
    for dep in dependencies:
        deps_by_task.setdefault(dep.task_id, []).append(
            f"{dep.depends_on.title} ({dep.dependency_type.value})"
        )

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "ID", "Tarefa", "Início", "Fim", "Duração (dias)", "Prioridade", "Status",
        "Marco", "Caminho crítico", "Custo", "Dependências",
    ])
    for task in tasks:
        duration = (
            (task.due_date - task.start_date).days if task.start_date and task.due_date else ""
        )
        writer.writerow([
            task.id,
            task.title,
            task.start_date.strftime("%d/%m/%Y") if task.start_date else "",
            task.due_date.strftime("%d/%m/%Y") if task.due_date else "",
            duration,
            task.priority.value,
            task.status.value,
            "Sim" if task.is_milestone else "Não",
            "Sim" if task.id in critical_ids else "Não",
            task_cost(task),
            "; ".join(deps_by_task.get(task.id, [])),
        ])
    buffer.seek(0)
    filename = f"gantt-{project.name}.csv".replace(" ", "-")
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
