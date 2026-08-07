from datetime import datetime, timezone
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
    WhatsAppStatusOut, WhatsAppQrOut, WhatsAppChatOut, WhatsAppMonitorRequest, WhatsAppWebhookMessage,
    WhatsAppAnalyzeRequest, WhatsAppMessageOut,
)
from app.schemas.ai_tasks import TaskSuggestionOut

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

_TIMEOUT = 10.0


def _service_url(path: str) -> str:
    return f"{settings.WHATSAPP_SERVICE_URL}{path}"


def _call_service(method: str, path: str) -> dict:
    try:
        response = httpx.request(method, _service_url(path), timeout=_TIMEOUT)
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
    return _status_out(db, connection, current_user.id)


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
    return _status_out(db, connection, current_user.id)


@router.get("/chats", response_model=list[WhatsAppChatOut])
def list_chats(current_user: User = Depends(get_current_user)):
    data = _call_service("GET", f"/chats/{current_user.id}")
    return [WhatsAppChatOut(**chat) for chat in data.get("chats", [])]


@router.get("/messages", response_model=list[WhatsAppMessageOut])
def list_messages(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    connection = whatsapp_crud.get_connection(db, current_user.id)
    if not connection or not connection.monitored_chat_jid:
        return []
    return whatsapp_crud.get_recent_messages(db, connection.id)


@router.post("/monitor", response_model=WhatsAppStatusOut)
def set_monitored_chat(
    body: WhatsAppMonitorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connection = whatsapp_crud.get_or_create_connection(db, current_user.id)
    connection = whatsapp_crud.set_monitored_chat(db, connection, body.chat_jid, body.chat_name)
    return _status_out(db, connection, current_user.id)


@router.post("/disconnect", response_model=WhatsAppStatusOut)
def disconnect(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    connection = whatsapp_crud.get_or_create_connection(db, current_user.id)
    _call_service("POST", f"/disconnect/{current_user.id}")
    connection = whatsapp_crud.reset_connection(db, connection)
    return _status_out(db, connection, current_user.id)


@router.post("/webhook/message", status_code=status.HTTP_204_NO_CONTENT)
def receive_message(
    body: WhatsAppWebhookMessage,
    db: Session = Depends(get_db),
    x_webhook_secret: str | None = Header(default=None),
):
    if not settings.WHATSAPP_WEBHOOK_SECRET or x_webhook_secret != settings.WHATSAPP_WEBHOOK_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Segredo de webhook inválido.")

    connection = whatsapp_crud.get_connection(db, body.user_id)
    if not connection or connection.monitored_chat_jid != body.chat_jid:
        return

    whatsapp_crud.add_message(
        db,
        connection.id,
        body.sender,
        body.text,
        datetime.fromtimestamp(body.timestamp, tz=timezone.utc),
    )


@router.post("/analyze", response_model=list[TaskSuggestionOut])
def analyze_pending_messages(
    body: WhatsAppAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_workspace_member(db, body.workspace_id, current_user.id)
    connection = whatsapp_crud.get_connection(db, current_user.id)
    if not connection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WhatsApp não conectado.")

    messages = whatsapp_crud.get_unprocessed_messages(db, connection.id)
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


def _status_out(db: Session, connection, user_id: int) -> WhatsAppStatusOut:
    return WhatsAppStatusOut(
        status=connection.status.value,
        phone_number=connection.phone_number,
        monitored_chat_jid=connection.monitored_chat_jid,
        monitored_chat_name=connection.monitored_chat_name,
        pending_message_count=whatsapp_crud.count_unprocessed(db, connection.id),
    )
