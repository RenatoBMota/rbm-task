from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    standard_rate: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    workspace: Mapped["Workspace"] = relationship("Workspace")
    assignments: Mapped[list["ResourceAssignment"]] = relationship(
        "ResourceAssignment", back_populates="resource", cascade="all, delete-orphan"
    )


class ResourceAssignment(Base):
    __tablename__ = "resource_assignments"
    __table_args__ = (UniqueConstraint("task_id", "resource_id", name="uq_resource_assignment"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id"), nullable=False)
    allocation_percent: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_coordinator: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    task: Mapped["Task"] = relationship("Task", back_populates="resource_assignments")
    resource: Mapped["Resource"] = relationship("Resource", back_populates="assignments")
