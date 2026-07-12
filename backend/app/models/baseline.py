from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class GanttBaseline(Base):
    __tablename__ = "gantt_baselines"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project: Mapped["Project"] = relationship("Project")
    tasks: Mapped[list["GanttBaselineTask"]] = relationship(
        "GanttBaselineTask", back_populates="baseline", cascade="all, delete-orphan"
    )


class GanttBaselineTask(Base):
    __tablename__ = "gantt_baseline_tasks"
    __table_args__ = (UniqueConstraint("baseline_id", "task_id", name="uq_baseline_task"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    baseline_id: Mapped[int] = mapped_column(ForeignKey("gantt_baselines.id"), nullable=False)
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    baseline: Mapped["GanttBaseline"] = relationship("GanttBaseline", back_populates="tasks")
