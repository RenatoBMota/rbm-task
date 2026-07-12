from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Text, ForeignKey, DateTime, Float, Enum, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class IndicatorType(str, PyEnum):
    QUANTITY = "quantity"
    VALUE = "value"
    PERCENTAGE = "percentage"
    DECIMAL = "decimal"
    INTEGER = "integer"


class KRCadence(str, PyEnum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class KRDirection(str, PyEnum):
    INCREASE = "increase"
    DECREASE = "decrease"


class Objective(Base):
    __tablename__ = "objectives"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    key_results: Mapped[list["KeyResult"]] = relationship(
        "KeyResult", back_populates="objective", cascade="all, delete-orphan", order_by="KeyResult.code"
    )


class KeyResult(Base):
    __tablename__ = "key_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    objective_id: Mapped[int] = mapped_column(ForeignKey("objectives.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    indicator_type: Mapped[IndicatorType] = mapped_column(Enum(IndicatorType), default=IndicatorType.QUANTITY)
    direction: Mapped[KRDirection] = mapped_column(Enum(KRDirection), default=KRDirection.INCREASE)
    cadence: Mapped[KRCadence] = mapped_column(Enum(KRCadence), default=KRCadence.WEEKLY)
    baseline_value: Mapped[float] = mapped_column(Float, default=0)
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    objective: Mapped["Objective"] = relationship("Objective", back_populates="key_results")
    checkins: Mapped[list["KeyResultCheckIn"]] = relationship(
        "KeyResultCheckIn", back_populates="key_result", cascade="all, delete-orphan",
        order_by="KeyResultCheckIn.period_end",
    )
    initiatives: Mapped[list["Initiative"]] = relationship(
        "Initiative", back_populates="key_result", cascade="all, delete-orphan"
    )


class KeyResultCheckIn(Base):
    __tablename__ = "key_result_checkins"

    id: Mapped[int] = mapped_column(primary_key=True)
    key_result_id: Mapped[int] = mapped_column(ForeignKey("key_results.id"), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    key_result: Mapped["KeyResult"] = relationship("KeyResult", back_populates="checkins")


class Initiative(Base):
    __tablename__ = "initiatives"

    id: Mapped[int] = mapped_column(primary_key=True)
    key_result_id: Mapped[int] = mapped_column(ForeignKey("key_results.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    weight_percent: Mapped[float] = mapped_column(Float, default=0)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    key_result: Mapped["KeyResult"] = relationship("KeyResult", back_populates="initiatives")
    tasks: Mapped[list["OkrTask"]] = relationship(
        "OkrTask", back_populates="initiative", cascade="all, delete-orphan"
    )


class OkrTask(Base):
    __tablename__ = "okr_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    initiative_id: Mapped[int] = mapped_column(ForeignKey("initiatives.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    weight_percent: Mapped[float] = mapped_column(Float, default=0)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    initiative: Mapped["Initiative"] = relationship("Initiative", back_populates="tasks")
    actions: Mapped[list["OkrAction"]] = relationship(
        "OkrAction", back_populates="task", cascade="all, delete-orphan"
    )


class OkrAction(Base):
    __tablename__ = "okr_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("okr_tasks.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    weight_percent: Mapped[float] = mapped_column(Float, default=0)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    task: Mapped["OkrTask"] = relationship("OkrTask", back_populates="actions")
