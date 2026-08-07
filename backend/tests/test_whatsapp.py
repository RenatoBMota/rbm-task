from tests.conftest import register_and_login, auth_headers, get_default_workspace_id, create_project
from app.core.config import settings
import app.api.v1.whatsapp as whatsapp_module


def test_connect_creates_connection_and_calls_service(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        whatsapp_module, "_call_service", lambda method, path, json=None: calls.append((method, path)) or {}
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
        whatsapp_module, "_call_service", lambda method, path, json=None: {"status": "connected", "phone": "5511999998888"}
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
    monkeypatch.setattr(whatsapp_module, "_call_service", lambda method, path, json=None: {"qr": "data:image/png;base64,xxx"})

    token = register_and_login(client)
    headers = auth_headers(token)

    response = client.get("/api/v1/whatsapp/qr", headers=headers)
    assert response.status_code == 200
    assert response.json()["qr"] == "data:image/png;base64,xxx"


def _send_webhook_message(client, user_id, chat_jid, chat_name, sender, text, timestamp, from_me=False):
    return client.post(
        "/api/v1/whatsapp/webhook/message",
        json={
            "user_id": user_id, "chat_jid": chat_jid, "chat_name": chat_name,
            "sender": sender, "text": text, "timestamp": timestamp, "from_me": from_me,
        },
        headers={"X-Webhook-Secret": "correct-secret"},
    )


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


def test_webhook_buffers_messages_across_chats(client, monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_WEBHOOK_SECRET", "correct-secret")
    monkeypatch.setattr(whatsapp_module, "_call_service", lambda method, path, json=None: {"status": "connected", "chats": []})

    token = register_and_login(client)
    headers = auth_headers(token)
    user_id = client.get("/api/v1/users/me", headers=headers).json()["id"]

    # No connection yet in DB until /connect or /status runs.
    client.get("/api/v1/whatsapp/status", headers=headers)

    r1 = _send_webhook_message(client, user_id, "123@g.us", "Equipe", "João", "checar estoque", 1700000000)
    assert r1.status_code == 204

    r2 = _send_webhook_message(client, user_id, "999@g.us", "Outro grupo", "Maria", "mensagem qualquer", 1700000001)
    assert r2.status_code == 204

    status_response = client.get("/api/v1/whatsapp/status", headers=headers)
    assert status_response.json()["pending_message_count"] == 2


def test_chats_lists_summaries_ordered_by_last_message(client, monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_WEBHOOK_SECRET", "correct-secret")
    monkeypatch.setattr(whatsapp_module, "_call_service", lambda method, path, json=None: {"status": "connected", "chats": []})

    token = register_and_login(client)
    headers = auth_headers(token)
    user_id = client.get("/api/v1/users/me", headers=headers).json()["id"]
    client.get("/api/v1/whatsapp/status", headers=headers)

    _send_webhook_message(client, user_id, "123@g.us", "Equipe Operações", "João", "checar estoque", 1700000000)
    _send_webhook_message(client, user_id, "999@g.us", "Outro grupo", "Maria", "mensagem mais recente", 1700000100)

    response = client.get("/api/v1/whatsapp/chats", headers=headers)
    assert response.status_code == 200
    chats = response.json()
    assert [c["jid"] for c in chats] == ["999@g.us", "123@g.us"]
    assert chats[0]["last_message_text"] == "mensagem mais recente"
    assert chats[0]["unread_count"] == 1


def test_messages_lists_history_for_a_chat(client, monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_WEBHOOK_SECRET", "correct-secret")
    monkeypatch.setattr(whatsapp_module, "_call_service", lambda method, path, json=None: {"status": "connected"})

    token = register_and_login(client)
    headers = auth_headers(token)
    user_id = client.get("/api/v1/users/me", headers=headers).json()["id"]
    client.get("/api/v1/whatsapp/status", headers=headers)

    _send_webhook_message(client, user_id, "123@g.us", "Equipe", "João", "checar estoque", 1700000000)
    _send_webhook_message(client, user_id, "999@g.us", "Outro", "Maria", "não deve aparecer", 1700000001)

    response = client.get("/api/v1/whatsapp/messages", params={"chat_jid": "123@g.us"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["sender_name"] == "João"
    assert body[0]["chat_jid"] == "123@g.us"
    assert body[0]["is_processed"] is False


def test_opening_a_chat_marks_it_read_until_a_new_message_arrives(client, monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_WEBHOOK_SECRET", "correct-secret")
    monkeypatch.setattr(whatsapp_module, "_call_service", lambda method, path, json=None: {"status": "connected", "chats": []})

    token = register_and_login(client)
    headers = auth_headers(token)
    user_id = client.get("/api/v1/users/me", headers=headers).json()["id"]
    client.get("/api/v1/whatsapp/status", headers=headers)

    _send_webhook_message(client, user_id, "123@g.us", "Equipe", "João", "checar estoque", 1700000000)

    chats_before = client.get("/api/v1/whatsapp/chats", headers=headers).json()
    assert chats_before[0]["unread_count"] == 1

    # Opening the chat (fetching its messages) marks it read.
    client.get("/api/v1/whatsapp/messages", params={"chat_jid": "123@g.us"}, headers=headers)

    chats_after = client.get("/api/v1/whatsapp/chats", headers=headers).json()
    assert chats_after[0]["unread_count"] == 0

    # A new message brings the badge back.
    _send_webhook_message(client, user_id, "123@g.us", "Equipe", "João", "mais uma", 1700000050)
    chats_final = client.get("/api/v1/whatsapp/chats", headers=headers).json()
    assert chats_final[0]["unread_count"] == 1


def test_send_message_requires_connection(client):
    token = register_and_login(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/v1/whatsapp/send", json={"chat_jid": "123@g.us", "text": "oi"}, headers=headers
    )
    assert response.status_code == 404


def test_send_message_calls_service(client, monkeypatch):
    monkeypatch.setattr(whatsapp_module, "_call_service", lambda method, path, json=None: {"status": "connected"})

    token = register_and_login(client)
    headers = auth_headers(token)
    user_id = client.get("/api/v1/users/me", headers=headers).json()["id"]
    client.get("/api/v1/whatsapp/status", headers=headers)

    calls = []
    monkeypatch.setattr(
        whatsapp_module, "_call_service", lambda method, path, json=None: calls.append((method, path, json)) or {}
    )

    response = client.post(
        "/api/v1/whatsapp/send", json={"chat_jid": "123@g.us", "text": "oi"}, headers=headers
    )
    assert response.status_code == 204
    assert calls == [("POST", f"/send/{user_id}", {"jid": "123@g.us", "text": "oi"})]


def test_disconnect_resets_connection(client, monkeypatch):
    monkeypatch.setattr(whatsapp_module, "_call_service", lambda method, path, json=None: {})

    token = register_and_login(client)
    headers = auth_headers(token)
    client.post("/api/v1/whatsapp/connect", headers=headers)

    response = client.post("/api/v1/whatsapp/disconnect", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "disconnected"


def test_analyze_uses_shared_extraction_and_marks_messages_processed(client, monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_WEBHOOK_SECRET", "correct-secret")
    monkeypatch.setattr(whatsapp_module, "_call_service", lambda method, path, json=None: {"status": "connected"})

    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = create_project(client, headers, workspace_id, name="Logística Norte")
    user_id = client.get("/api/v1/users/me", headers=headers).json()["id"]
    client.get("/api/v1/whatsapp/status", headers=headers)

    _send_webhook_message(client, user_id, "123@g.us", "Equipe", "João", "auditoria no fornecedor X", 1700000000)
    message_id = client.get(
        "/api/v1/whatsapp/messages", params={"chat_jid": "123@g.us"}, headers=headers
    ).json()[0]["id"]

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
        "/api/v1/whatsapp/analyze",
        json={"workspace_id": workspace_id, "message_ids": [message_id]},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Auditoria no fornecedor X"
    assert "João" in captured_text["text"]
    assert "auditoria no fornecedor X" in captured_text["text"]

    # Second call with the same (now processed) id has nothing left to analyze.
    response2 = client.post(
        "/api/v1/whatsapp/analyze",
        json={"workspace_id": workspace_id, "message_ids": [message_id]},
        headers=headers,
    )
    assert response2.status_code == 200
    status_response = client.get("/api/v1/whatsapp/status", headers=headers)
    assert status_response.json()["pending_message_count"] == 0


def test_analyze_requires_workspace_membership(client):
    token_a = register_and_login(client, email="wa1@rbm.com")
    workspace_a = get_default_workspace_id(client, auth_headers(token_a))

    token_b = register_and_login(client, email="wa2@rbm.com")
    response = client.post(
        "/api/v1/whatsapp/analyze",
        json={"workspace_id": workspace_a, "message_ids": [1]},
        headers=auth_headers(token_b),
    )
    assert response.status_code == 404


def test_analyze_without_connection_returns_404(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)

    response = client.post(
        "/api/v1/whatsapp/analyze",
        json={"workspace_id": workspace_id, "message_ids": [1]},
        headers=headers,
    )
    assert response.status_code == 404
