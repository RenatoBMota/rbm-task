from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.task import Task, TaskStatus
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.core.exceptions import ProjectDateRangeError


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_project(db: Session, project_id: int) -> Project | None:
    return db.query(Project).filter(Project.id == project_id).first()


def get_projects(
    db: Session,
    workspace_id: int,
    skip: int = 0,
    limit: int = 100,
    include_archived: bool = False,
    templates_only: bool = False,
) -> list[Project]:
    query = db.query(Project).filter(Project.workspace_id == workspace_id)
    if not include_archived:
        query = query.filter(Project.is_archived == False)
    if templates_only:
        query = query.filter(Project.is_template == True)
    return query.offset(skip).limit(limit).all()


def create_project(db: Session, project_in: ProjectCreate, owner_id: int) -> Project:
    db_project = Project(**project_in.model_dump(), owner_id=owner_id)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def update_project(db: Session, project: Project, project_in: ProjectUpdate) -> Project:
    update_data = project_in.model_dump(exclude_unset=True)

    if "start_date" in update_data or "end_date" in update_data:
        new_start = _aware(update_data.get("start_date", project.start_date))
        new_end = _aware(update_data.get("end_date", project.end_date))
        if new_end < new_start:
            raise ProjectDateRangeError("A data de término não pode ser anterior à data de início.")

        tasks = db.query(Task).filter(Task.project_id == project.id, Task.is_archived == False).all()
        out_of_range = [
            t for t in tasks
            if (t.start_date and not (new_start <= _aware(t.start_date) <= new_end))
            or (t.due_date and not (new_start <= _aware(t.due_date) <= new_end))
        ]
        if out_of_range:
            titles = ", ".join(f'"{t.title}"' for t in out_of_range[:5])
            suffix = f" e mais {len(out_of_range) - 5} tarefa(s)" if len(out_of_range) > 5 else ""
            raise ProjectDateRangeError(
                f"Não é possível ajustar o prazo do projeto: {titles}{suffix} ficariam fora do novo "
                "intervalo. Reagende essas tarefas antes de encurtar a duração do projeto."
            )

    for field, value in update_data.items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    db.delete(project)
    db.commit()


def duplicate_project(db: Session, source: Project, new_name: str, owner_id: int) -> Project:
    new_project = Project(
        name=new_name,
        description=source.description,
        start_date=source.start_date,
        end_date=source.end_date,
        color=source.color,
        icon=source.icon,
        owner_id=owner_id,
        workspace_id=source.workspace_id,
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    top_level_tasks = db.query(Task).filter(
        Task.project_id == source.id, Task.parent_id == None
    ).order_by(Task.position).all()
    for position, task in enumerate(top_level_tasks):
        db.add(Task(
            title=task.title,
            description=task.description,
            priority=task.priority,
            status=TaskStatus.TODO,
            estimated_minutes=task.estimated_minutes,
            project_id=new_project.id,
            assignee_id=owner_id,
            position=position,
        ))
    db.commit()
    return new_project
