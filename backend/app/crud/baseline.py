from sqlalchemy.orm import Session
from app.models.baseline import GanttBaseline, GanttBaselineTask
from app.models.task import Task


def get_baseline(db: Session, baseline_id: int) -> GanttBaseline | None:
    return db.query(GanttBaseline).filter(GanttBaseline.id == baseline_id).first()


def get_project_baselines(db: Session, project_id: int) -> list[GanttBaseline]:
    return (
        db.query(GanttBaseline)
        .filter(GanttBaseline.project_id == project_id)
        .order_by(GanttBaseline.created_at.desc())
        .all()
    )


def create_baseline(
    db: Session, project_id: int, name: str, created_by_id: int, tasks: list[Task]
) -> GanttBaseline:
    baseline = GanttBaseline(project_id=project_id, name=name, created_by_id=created_by_id)
    db.add(baseline)
    db.commit()
    db.refresh(baseline)
    for task in tasks:
        db.add(
            GanttBaselineTask(
                baseline_id=baseline.id,
                task_id=task.id,
                title=task.title,
                start_date=task.start_date,
                due_date=task.due_date,
            )
        )
    db.commit()
    db.refresh(baseline)
    return baseline


def delete_baseline(db: Session, baseline: GanttBaseline) -> None:
    db.delete(baseline)
    db.commit()
