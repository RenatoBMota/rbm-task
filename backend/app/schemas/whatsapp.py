from datetime import datetime
from pydantic import BaseModel, Field


class WhatsAppStatusOut(BaseModel):
    status: str
    phone_number: str | None
    monitored_chat_jid: str | None
    monitored_chat_name: str | None
    pending_message_count: int


class WhatsAppQrOut(BaseModel):
    qr: str | None


class WhatsAppChatOut(BaseModel):
    jid: str
    name: str


class WhatsAppMonitorRequest(BaseModel):
    chat_jid: str = Field(min_length=1)
    chat_name: str = Field(min_length=1)


class WhatsAppAnalyzeRequest(BaseModel):
    workspace_id: int


class WhatsAppMessageOut(BaseModel):
    id: int
    sender_name: str
    text: str
    whatsapp_timestamp: datetime
    is_processed: bool

    model_config = {"from_attributes": True}


class WhatsAppWebhookMessage(BaseModel):
    user_id: int
    chat_jid: str
    chat_name: str
    sender: str
    text: str = Field(min_length=1, max_length=8000)
    timestamp: int
