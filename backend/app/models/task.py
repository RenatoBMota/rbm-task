from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Text, ForeignKey, DateTime, Boolean, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class TaskPriority(str, PyEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class TaskStatus(str, PyEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority), default=TaskPriority.P4
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.TODO
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    project: Mapped["Project | None"] = relationship("Project", back_populates="tasks")
    assignee: Mapped["User | None"] = relationship("User", back_populates="tasks")
    subtasks: Mapped[list["Task"]] = relationship("Task", back_populates="parent")
    parent: Mapped["Task | None"] = relationship("Task", back_populates="subtasks", remote_side="Task.id")
    checklist_items: Mapped[list["ChecklistItem"]] = relationship(
        "ChecklistItem", back_populates="task", cascade="all, delete-orphan", order_by="ChecklistItem.position"
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="task", cascade="all, delete-orphan", order_by="Comment.created_at"
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment", back_populates="task", cascade="all, delete-orphan"
    )
