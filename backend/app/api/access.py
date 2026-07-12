from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.crud.task import get_task
from app.crud.project import get_project
from app.crud.workspace import get_member
from app.models.task import Task


def require_project_member(db: Session, project_id: int, user_id: int) -> None:
    project = get_project(db, project_id)
    if not project or not get_member(db, project.workspace_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado")


def require_workspace_member(db: Session, workspace_id: int, user_id: int) -> None:
    if not get_member(db, workspace_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Área de trabalho não encontrada")


def require_task_access(db: Session, task_id: int, user_id: int) -> Task:
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    if task.project_id:
        project = get_project(db, task.project_id)
        if not project or not get_member(db, project.workspace_id, user_id):
            raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    elif task.assignee_id != user_id:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return task
