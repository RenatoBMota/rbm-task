from sqlalchemy import Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.task import TaskPriority


class SLAPolicy(Base):
    __tablename__ = "sla_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    priority: Mapped[TaskPriority] = mapped_column(Enum(TaskPriority), unique=True, nullable=False)
    target_hours: Mapped[int] = mapped_column(Integer, nullable=False)
