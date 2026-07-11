from sqlalchemy.orm import Session
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


def get_project(db: Session, project_id: int, owner_id: int) -> Project | None:
    return db.query(Project).filter(
        Project.id == project_id, Project.owner_id == owner_id
    ).first()


def get_projects(db: Session, owner_id: int, skip: int = 0, limit: int = 100) -> list[Project]:
    return db.query(Project).filter(
        Project.owner_id == owner_id, Project.is_archived == False
    ).offset(skip).limit(limit).all()


def create_project(db: Session, project_in: ProjectCreate, owner_id: int) -> Project:
    db_project = Project(**project_in.model_dump(), owner_id=owner_id)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def update_project(db: Session, project: Project, project_in: ProjectUpdate) -> Project:
    update_data = project_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    db.delete(project)
    db.commit()
