from datetime import datetime, timezone
from sqlalchemy import func
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


def reset_connection(db: Session, connection: WhatsAppConnection) -> WhatsAppConnection:
    connection.status = WhatsAppConnectionStatus.DISCONNECTED
    connection.phone_number = None
    connection.connected_at = None
    db.commit()
    db.refresh(connection)
    return connection


def add_message(
    db: Session,
    connection_id: int,
    chat_jid: str,
    chat_name: str,
    sender_name: str,
    text: str,
    whatsapp_timestamp: datetime,
    is_from_me: bool = False,
) -> WhatsAppMessage:
    message = WhatsAppMessage(
        connection_id=connection_id,
        chat_jid=chat_jid,
        chat_name=chat_name,
        sender_name=sender_name,
        text=text,
        whatsapp_timestamp=whatsapp_timestamp,
        is_from_me=is_from_me,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def bulk_add_historical_messages(db: Session, connection_id: int, entries: list[dict]) -> None:
    # Historical backfill (from the initial WhatsApp pairing sync) - marked
    # already read since these predate the user opening the app, unlike a
    # genuinely new incoming message.
    objects = [
        WhatsAppMessage(
            connection_id=connection_id,
            chat_jid=entry["chat_jid"],
            chat_name=entry["chat_name"],
            sender_name=entry["sender"],
            text=entry["text"],
            whatsapp_timestamp=entry["whatsapp_timestamp"],
            is_from_me=entry["is_from_me"],
            is_read=True,
        )
        for entry in entries
    ]
    db.add_all(objects)
    db.commit()


def get_recent_messages(db: Session, connection_id: int, chat_jid: str, limit: int = 50) -> list[WhatsAppMessage]:
    messages = (
        db.query(WhatsAppMessage)
        .filter(WhatsAppMessage.connection_id == connection_id, WhatsAppMessage.chat_jid == chat_jid)
        .order_by(WhatsAppMessage.whatsapp_timestamp.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(messages))


def get_chat_summaries(db: Session, connection_id: int) -> list[dict]:
    rows = (
        db.query(
            WhatsAppMessage.chat_jid,
            WhatsAppMessage.chat_name,
            func.max(WhatsAppMessage.whatsapp_timestamp).label("last_at"),
        )
        .filter(WhatsAppMessage.connection_id == connection_id)
        .group_by(WhatsAppMessage.chat_jid, WhatsAppMessage.chat_name)
        .order_by(func.max(WhatsAppMessage.whatsapp_timestamp).desc())
        .all()
    )
    summaries = []
    for row in rows:
        last_message = (
            db.query(WhatsAppMessage)
            .filter(WhatsAppMessage.connection_id == connection_id, WhatsAppMessage.chat_jid == row.chat_jid)
            .order_by(WhatsAppMessage.whatsapp_timestamp.desc())
            .first()
        )
        unread_count = (
            db.query(WhatsAppMessage)
            .filter(
                WhatsAppMessage.connection_id == connection_id,
                WhatsAppMessage.chat_jid == row.chat_jid,
                WhatsAppMessage.is_read == False,
                WhatsAppMessage.is_from_me == False,
            )
            .count()
        )
        summaries.append(
            {
                "jid": row.chat_jid,
                "name": row.chat_name,
                "last_message_text": last_message.text if last_message else None,
                "last_message_at": row.last_at,
                "unread_count": unread_count,
            }
        )
    return summaries


def mark_chat_read(db: Session, connection_id: int, chat_jid: str) -> None:
    db.query(WhatsAppMessage).filter(
        WhatsAppMessage.connection_id == connection_id,
        WhatsAppMessage.chat_jid == chat_jid,
        WhatsAppMessage.is_read == False,
        WhatsAppMessage.is_from_me == False,
    ).update({"is_read": True})
    db.commit()


def delete_chat_messages(db: Session, connection_id: int, chat_jid: str) -> None:
    db.query(WhatsAppMessage).filter(
        WhatsAppMessage.connection_id == connection_id, WhatsAppMessage.chat_jid == chat_jid
    ).delete()
    db.commit()


def get_messages_by_ids(db: Session, connection_id: int, message_ids: list[int]) -> list[WhatsAppMessage]:
    return (
        db.query(WhatsAppMessage)
        .filter(WhatsAppMessage.connection_id == connection_id, WhatsAppMessage.id.in_(message_ids))
        .order_by(WhatsAppMessage.whatsapp_timestamp)
        .all()
    )


def count_unprocessed(db: Session, connection_id: int) -> int:
    return (
        db.query(WhatsAppMessage)
        .filter(
            WhatsAppMessage.connection_id == connection_id,
            WhatsAppMessage.is_processed == False,
            WhatsAppMessage.is_from_me == False,
        )
        .count()
    )


def mark_processed(db: Session, messages: list[WhatsAppMessage]) -> None:
    for message in messages:
        message.is_processed = True
    db.commit()
