from tests.conftest import register_and_login, auth_headers, get_default_workspace_id, create_project
from app.core.config import settings
import app.api.v1.whatsapp as whatsapp_module


def test_connect_creates_connection_and_calls_service(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        whatsapp_module, "_call_service", lambda method, path: calls.append((method, path)) or {}
    )

    token = register_and_login(client)
    headers = auth_headers(token)

    user_id = client.get("/api/v1/users/me", headers=headers).json()["id"]

    response = client.post("/api/v1/whatsapp/connect", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "connecting"
    assert calls == [("POST", f"/connect/{user_id}")]


def test_status_syncs_phone_and_status_from_service(client, monkeypatch):
    monkeypatch.setattr(
        whatsapp_module, "_call_service", lambda method, path: {"status": "connected", "phone": "5511999998888"}
    )

    token = register_and_login(client)
    headers = auth_headers(token)

    response = client.get("/api/v1/whatsapp/status", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "connected"
    assert body["phone_number"] == "5511999998888"
    assert body["pending_message_count"] == 0


def test_qr_returns_data_from_service(client, monkeypatch):
    monkeypatch.setattr(whatsapp_module, "_call_service", lambda method, path: {"qr": "data:image/png;base64,xxx"})

    token = register_and_login(client)
    headers = auth_headers(token)

    response = client.get("/api/v1/whatsapp/qr", headers=headers)
    assert response.status_code == 200
    assert response.json()["qr"] == "data:image/png;base64,xxx"


def test_chats_lists_from_service(client, monkeypatch):
    monkeypatch.setattr(
        whatsapp_module,
        "_call_service",
        lambda method, path: {"chats": [{"jid": "123@g.us", "name": "Equipe Operações"}]},
    )

    token = register_and_login(client)
    headers = auth_headers(token)

    response = client.get("/api/v1/whatsapp/chats", headers=headers)
    assert response.status_code == 200
    assert response.json() == [{"jid": "123@g.us", "name": "Equipe Operações"}]


def test_monitor_sets_chat_on_connection(client):
    token = register_and_login(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/v1/whatsapp/monitor",
        json={"chat_jid": "123@g.us", "chat_name": "Equipe Operações"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["monitored_chat_jid"] == "123@g.us"
    assert body["monitored_chat_name"] == "Equipe Operações"


def test_disconnect_resets_connection(client, monkeypatch):
    monkeypatch.setattr(whatsapp_module, "_call_service", lambda method, path: {})

    token = register_and_login(client)
    headers = auth_headers(token)
    client.post(
        "/api/v1/whatsapp/monitor", json={"chat_jid": "123@g.us", "chat_name": "Equipe"}, headers=headers
    )

    response = client.post("/api/v1/whatsapp/disconnect", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "disconnected"
    assert body["monitored_chat_jid"] is None
    assert body["monitored_chat_name"] is None


def test_webhook_rejects_wrong_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_WEBHOOK_SECRET", "correct-secret")

    response = client.post(
        "/api/v1/whatsapp/webhook/message",
        json={
            "user_id": 1, "chat_jid": "123@g.us", "chat_name": "Equipe",
            "sender": "João", "text": "checar estoque", "timestamp": 1700000000,
        },
        headers={"X-Webhook-Secret": "wrong-secret"},
    )
    assert response.status_code == 401


def test_webhook_buffers_message_only_for_monitored_chat(client, monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_WEBHOOK_SECRET", "correct-secret")
    monkeypatch.setattr(whatsapp_module, "_call_service", lambda method, path: {"status": "connected"})

    token = register_and_login(client)
    headers = auth_headers(token)
    user_id = client.get("/api/v1/users/me", headers=headers).json()["id"]

    client.post(
        "/api/v1/whatsapp/monitor", json={"chat_jid": "123@g.us", "chat_name": "Equipe"}, headers=headers
    )

    # Message from the monitored chat: buffered.
    r1 = client.post(
        "/api/v1/whatsapp/webhook/message",
        json={
            "user_id": user_id, "chat_jid": "123@g.us", "chat_name": "Equipe",
            "sender": "João", "text": "checar estoque", "timestamp": 1700000000,
        },
        headers={"X-Webhook-Secret": "correct-secret"},
    )
    assert r1.status_code == 204

    # Message from a different (unmonitored) chat: silently ignored.
    r2 = client.post(
        "/api/v1/whatsapp/webhook/message",
        json={
            "user_id": user_id, "chat_jid": "999@g.us", "chat_name": "Outro grupo",
            "sender": "Maria", "text": "mensagem qualquer", "timestamp": 1700000001,
        },
        headers={"X-Webhook-Secret": "correct-secret"},
    )
    assert r2.status_code == 204

    status_response = client.get("/api/v1/whatsapp/status", headers=headers)
    assert status_response.json()["pending_message_count"] == 1


def test_analyze_uses_shared_extraction_and_marks_messages_processed(client, monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_WEBHOOK_SECRET", "correct-secret")

    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = create_project(client, headers, workspace_id, name="Logística Norte")
    user_id = client.get("/api/v1/users/me", headers=headers).json()["id"]

    client.post(
        "/api/v1/whatsapp/monitor", json={"chat_jid": "123@g.us", "chat_name": "Equipe"}, headers=headers
    )
    client.post(
        "/api/v1/whatsapp/webhook/message",
        json={
            "user_id": user_id, "chat_jid": "123@g.us", "chat_name": "Equipe",
            "sender": "João", "text": "auditoria no fornecedor X", "timestamp": 1700000000,
        },
        headers={"X-Webhook-Secret": "correct-secret"},
    )

    captured_text = {}

    def fake_suggest(db, workspace_id_arg, text):
        captured_text["text"] = text
        return [{
            "title": "Auditoria no fornecedor X", "description": None, "priority": "P2",
            "due_date": None, "estimated_minutes": None,
            "suggested_project_id": project["id"], "suggested_project_name": project["name"],
        }]

    monkeypatch.setattr(whatsapp_module, "suggest_tasks_for_workspace", fake_suggest)

    response = client.post(
        "/api/v1/whatsapp/analyze", json={"workspace_id": workspace_id}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Auditoria no fornecedor X"
    assert "João" in captured_text["text"]
    assert "auditoria no fornecedor X" in captured_text["text"]

    # Second call: messages were marked processed, nothing left to analyze.
    response2 = client.post(
        "/api/v1/whatsapp/analyze", json={"workspace_id": workspace_id}, headers=headers
    )
    assert response2.status_code == 200
    assert response2.json() == []


def test_analyze_requires_workspace_membership(client):
    token_a = register_and_login(client, email="wa1@rbm.com")
    workspace_a = get_default_workspace_id(client, auth_headers(token_a))

    token_b = register_and_login(client, email="wa2@rbm.com")
    response = client.post(
        "/api/v1/whatsapp/analyze",
        json={"workspace_id": workspace_a},
        headers=auth_headers(token_b),
    )
    assert response.status_code == 404


def test_analyze_without_connection_returns_404(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)

    response = client.post(
        "/api/v1/whatsapp/analyze", json={"workspace_id": workspace_id}, headers=headers
    )
    assert response.status_code == 404
