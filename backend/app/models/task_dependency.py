from enum import Enum as PyEnum
from sqlalchemy import ForeignKey, Integer, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class DependencyType(str, PyEnum):
    FINISH_START = "finish_start"
    START_START = "start_start"
    FINISH_FINISH = "finish_finish"
    START_FINISH = "start_finish"


class DependencyHardness(str, PyEnum):
    STRONG = "strong"
    RUBBER = "rubber"


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (UniqueConstraint("task_id", "depends_on_id", name="uq_task_dependency"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    depends_on_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    dependency_type: Mapped[DependencyType] = mapped_column(
        Enum(DependencyType), default=DependencyType.FINISH_START, nullable=False
    )
    lag_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hardness: Mapped[DependencyHardness] = mapped_column(
        Enum(DependencyHardness), default=DependencyHardness.STRONG, nullable=False
    )

    task: Mapped["Task"] = relationship("Task", foreign_keys=[task_id], back_populates="dependencies")
    depends_on: Mapped["Task"] = relationship("Task", foreign_keys=[depends_on_id])
