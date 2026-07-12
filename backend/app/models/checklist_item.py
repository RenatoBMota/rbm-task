from sqlalchemy import String, ForeignKey, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)

    task: Mapped["Task"] = relationship("Task", back_populates="checklist_items")
