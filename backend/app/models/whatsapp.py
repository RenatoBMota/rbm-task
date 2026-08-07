from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class WhatsAppConnectionStatus(str, PyEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    QR_PENDING = "qr_pending"
    CONNECTED = "connected"


class WhatsAppConnection(Base):
    __tablename__ = "whatsapp_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    status: Mapped[WhatsAppConnectionStatus] = mapped_column(
        Enum(WhatsAppConnectionStatus), default=WhatsAppConnectionStatus.DISCONNECTED
    )
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    monitored_chat_jid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    monitored_chat_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship("User")
    messages: Mapped[list["WhatsAppMessage"]] = relationship(
        "WhatsAppMessage", back_populates="connection", cascade="all, delete-orphan"
    )


class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    connection_id: Mapped[int] = mapped_column(
        ForeignKey("whatsapp_connections.id", ondelete="CASCADE"), nullable=False
    )
    sender_name: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    whatsapp_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    connection: Mapped["WhatsAppConnection"] = relationship("WhatsAppConnection", back_populates="messages")
