from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.whatsapp import WhatsAppConnection, WhatsAppMessage, WhatsAppConnectionStatus


def get_connection(db: Session, user_id: int) -> WhatsAppConnection | None:
    return db.query(WhatsAppConnection).filter(WhatsAppConnection.user_id == user_id).first()


def get_or_create_connection(db: Session, user_id: int) -> WhatsAppConnection:
    connection = get_connection(db, user_id)
    if connection:
        return connection
    connection = WhatsAppConnection(user_id=user_id, status=WhatsAppConnectionStatus.DISCONNECTED)
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection


def set_status(
    db: Session, connection: WhatsAppConnection, status: WhatsAppConnectionStatus, phone_number: str | None = None
) -> WhatsAppConnection:
    connection.status = status
    if phone_number:
        connection.phone_number = phone_number
    if status == WhatsAppConnectionStatus.CONNECTED and not connection.connected_at:
        connection.connected_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(connection)
    return connection


def set_monitored_chat(
    db: Session, connection: WhatsAppConnection, chat_jid: str, chat_name: str
) -> WhatsAppConnection:
    connection.monitored_chat_jid = chat_jid
    connection.monitored_chat_name = chat_name
    db.commit()
    db.refresh(connection)
    return connection


def reset_connection(db: Session, connection: WhatsAppConnection) -> WhatsAppConnection:
    connection.status = WhatsAppConnectionStatus.DISCONNECTED
    connection.phone_number = None
    connection.monitored_chat_jid = None
    connection.monitored_chat_name = None
    connection.connected_at = None
    db.commit()
    db.refresh(connection)
    return connection


def add_message(
    db: Session, connection_id: int, sender_name: str, text: str, whatsapp_timestamp: datetime
) -> WhatsAppMessage:
    message = WhatsAppMessage(
        connection_id=connection_id,
        sender_name=sender_name,
        text=text,
        whatsapp_timestamp=whatsapp_timestamp,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_unprocessed_messages(db: Session, connection_id: int) -> list[WhatsAppMessage]:
    return (
        db.query(WhatsAppMessage)
        .filter(WhatsAppMessage.connection_id == connection_id, WhatsAppMessage.is_processed == False)
        .order_by(WhatsAppMessage.whatsapp_timestamp)
        .all()
    )


def get_recent_messages(db: Session, connection_id: int, limit: int = 50) -> list[WhatsAppMessage]:
    messages = (
        db.query(WhatsAppMessage)
        .filter(WhatsAppMessage.connection_id == connection_id)
        .order_by(WhatsAppMessage.whatsapp_timestamp.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(messages))


def count_unprocessed(db: Session, connection_id: int) -> int:
    return (
        db.query(WhatsAppMessage)
        .filter(WhatsAppMessage.connection_id == connection_id, WhatsAppMessage.is_processed == False)
        .count()
    )


def mark_processed(db: Session, messages: list[WhatsAppMessage]) -> None:
    for message in messages:
        message.is_processed = True
    db.commit()
