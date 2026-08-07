from datetime import datetime, timezone
from urllib.parse import quote
import httpx
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_user
from app.api.access import require_workspace_member
from app.core.ai_task_extraction import suggest_tasks_for_workspace, AiNotConfiguredError, AiRequestError
from app.crud import whatsapp as whatsapp_crud
from app.models.whatsapp import WhatsAppConnectionStatus
from app.models.user import User
from app.schemas.whatsapp import (
    WhatsAppStatusOut, WhatsAppQrOut, WhatsAppChatSummary, WhatsAppMessageOut, WhatsAppSendRequest,
    WhatsAppWebhookMessage, WhatsAppAnalyzeRequest,
)
from app.schemas.ai_tasks import TaskSuggestionOut

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

_TIMEOUT = 10.0


def _sortable_datetime(value: datetime | None) -> datetime:
    # SQLite (used in tests) returns naive datetimes even for timezone=True
    # columns, while Postgres returns aware ones - normalize so sorting
    # never compares naive against aware.
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _service_url(path: str) -> str:
    return f"{settings.WHATSAPP_SERVICE_URL}{path}"


def _call_service(method: str, path: str, json: dict | None = None) -> dict:
    try:
        response = httpx.request(method, _service_url(path), json=json, timeout=_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Não foi possível se comunicar com o serviço do WhatsApp: {exc}",
        ) from exc


@router.post("/connect", response_model=WhatsAppStatusOut)
def connect(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    connection = whatsapp_crud.get_or_create_connection(db, current_user.id)
    _call_service("POST", f"/connect/{current_user.id}")
    whatsapp_crud.set_status(db, connection, WhatsAppConnectionStatus.CONNECTING)
    return _status_out(db, connection)


@router.get("/qr", response_model=WhatsAppQrOut)
def get_qr(current_user: User = Depends(get_current_user)):
    data = _call_service("GET", f"/qr/{current_user.id}")
    return WhatsAppQrOut(qr=data.get("qr"))


@router.get("/status", response_model=WhatsAppStatusOut)
def get_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    connection = whatsapp_crud.get_or_create_connection(db, current_user.id)
    live = _call_service("GET", f"/status/{current_user.id}")
    live_status = WhatsAppConnectionStatus(live.get("status", "disconnected"))
    if live_status != connection.status or live.get("phone"):
        connection = whatsapp_crud.set_status(db, connection, live_status, phone_number=live.get("phone"))
    return _status_out(db, connection)


@router.get("/chats", response_model=list[WhatsAppChatSummary])
def list_chats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    connection = whatsapp_crud.get_connection(db, current_user.id)
    if not connection:
        return []

    summaries = {s["jid"]: s for s in whatsapp_crud.get_chat_summaries(db, connection.id)}

    live = _call_service("GET", f"/chats/{current_user.id}")
    for chat in live.get("chats", []):
        if chat["jid"] not in summaries:
            summaries[chat["jid"]] = {
                "jid": chat["jid"],
                "name": chat["name"],
                "last_message_text": None,
                "last_message_at": None,
                "unread_count": 0,
            }

    ordered = sorted(summaries.values(), key=lambda s: _sortable_datetime(s["last_message_at"]), reverse=True)
    return [WhatsAppChatSummary(**s) for s in ordered]


@router.delete("/chats", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    chat_jid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    connection = whatsapp_crud.get_connection(db, current_user.id)
    if not connection:
        return
    whatsapp_crud.delete_chat_messages(db, connection.id, chat_jid)
    _call_service("DELETE", f"/chats/{current_user.id}/{quote(chat_jid, safe='')}")


@router.get("/messages", response_model=list[WhatsAppMessageOut])
def list_messages(
    chat_jid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    connection = whatsapp_crud.get_connection(db, current_user.id)
    if not connection:
        return []
    messages = whatsapp_crud.get_recent_messages(db, connection.id, chat_jid)
    whatsapp_crud.mark_chat_read(db, connection.id, chat_jid)
    return messages


@router.post("/send", status_code=status.HTTP_204_NO_CONTENT)
def send_message(
    body: WhatsAppSendRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    connection = whatsapp_crud.get_connection(db, current_user.id)
    if not connection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WhatsApp não conectado.")

    _call_service("POST", f"/send/{current_user.id}", json={"jid": body.chat_jid, "text": body.text})


@router.post("/disconnect", response_model=WhatsAppStatusOut)
def disconnect(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    connection = whatsapp_crud.get_or_create_connection(db, current_user.id)
    _call_service("POST", f"/disconnect/{current_user.id}")
    connection = whatsapp_crud.reset_connection(db, connection)
    return _status_out(db, connection)


@router.post("/webhook/message", status_code=status.HTTP_204_NO_CONTENT)
def receive_message(
    body: WhatsAppWebhookMessage,
    db: Session = Depends(get_db),
    x_webhook_secret: str | None = Header(default=None),
):
    if not settings.WHATSAPP_WEBHOOK_SECRET or x_webhook_secret != settings.WHATSAPP_WEBHOOK_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Segredo de webhook inválido.")

    connection = whatsapp_crud.get_connection(db, body.user_id)
    if not connection:
        return

    whatsapp_crud.add_message(
        db,
        connection.id,
        body.chat_jid,
        body.chat_name,
        body.sender,
        body.text,
        datetime.fromtimestamp(body.timestamp, tz=timezone.utc),
        is_from_me=body.from_me,
    )


@router.post("/analyze", response_model=list[TaskSuggestionOut])
def analyze_messages(
    body: WhatsAppAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_workspace_member(db, body.workspace_id, current_user.id)
    connection = whatsapp_crud.get_connection(db, current_user.id)
    if not connection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WhatsApp não conectado.")

    messages = whatsapp_crud.get_messages_by_ids(db, connection.id, body.message_ids)
    if not messages:
        return []

    text = "\n".join(f"[{m.sender_name}] {m.text}" for m in messages)
    try:
        suggestions = suggest_tasks_for_workspace(db, body.workspace_id, text)
    except AiNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except AiRequestError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    whatsapp_crud.mark_processed(db, messages)
    return suggestions


def _status_out(db: Session, connection) -> WhatsAppStatusOut:
    return WhatsAppStatusOut(
        status=connection.status.value,
        phone_number=connection.phone_number,
        pending_message_count=whatsapp_crud.count_unprocessed(db, connection.id),
    )
