from datetime import datetime
from pydantic import BaseModel, Field


class WhatsAppStatusOut(BaseModel):
    status: str
    phone_number: str | None
    pending_message_count: int


class WhatsAppQrOut(BaseModel):
    qr: str | None


class WhatsAppChatSummary(BaseModel):
    jid: str
    name: str
    last_message_text: str | None = None
    last_message_at: datetime | None = None
    pending_count: int = 0


class WhatsAppMessageOut(BaseModel):
    id: int
    chat_jid: str
    chat_name: str
    sender_name: str
    text: str
    whatsapp_timestamp: datetime
    is_from_me: bool
    is_processed: bool

    model_config = {"from_attributes": True}


class WhatsAppSendRequest(BaseModel):
    chat_jid: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=8000)


class WhatsAppAnalyzeRequest(BaseModel):
    workspace_id: int
    message_ids: list[int] = Field(min_length=1)


class WhatsAppWebhookMessage(BaseModel):
    user_id: int
    chat_jid: str
    chat_name: str
    sender: str
    text: str = Field(min_length=1, max_length=8000)
    timestamp: int
    from_me: bool = False
