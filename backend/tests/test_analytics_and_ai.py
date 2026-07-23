from tests.conftest import register_and_login, auth_headers, get_default_workspace_id, create_project
from app.core.config import settings
import app.api.v1.ai as ai_module


def _create_task(client, headers, **overrides):
    workspace_id = get_default_workspace_id(client, headers)
    project = create_project(client, headers, workspace_id)
    payload = {"title": "T", "project_id": project["id"], **overrides}
    return client.post("/api/v1/tasks", json=payload, headers=headers).json()


def test_analytics_endpoints_do_not_error_when_empty(client):
    token = register_and_login(client)
    headers = auth_headers(token)

    for path in (
        "/api/v1/analytics/completion-trend",
        "/api/v1/analytics/status-breakdown",
        "/api/v1/analytics/sla-compliance",
    ):
        response = client.get(path, headers=headers)
        assert response.status_code == 200


def test_sla_compliance_counts_task(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    _create_task(client, headers)

    response = client.get("/api/v1/analytics/sla-compliance", headers=headers)
    body = response.json()
    assert body["total"] == 1
    assert body["on_time"] == 1


def test_ai_priority_suggestions_ranks_by_urgency(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    _create_task(client, headers, title="Baixa", priority="P4")
    _create_task(client, headers, title="Alta", priority="P1")

    response = client.get("/api/v1/ai/priority-suggestions", headers=headers)
    assert response.status_code == 200
    suggestions = response.json()
    assert suggestions[0]["title"] == "Alta"


def test_ai_time_estimate_with_no_history(client):
    token = register_and_login(client)
    headers = auth_headers(token)

    response = client.get("/api/v1/ai/time-estimate", headers=headers)
    assert response.status_code == 200
    assert response.json()["sample_size"] == 0


def test_ai_risk_tasks_empty_without_due_dates(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    _create_task(client, headers)

    response = client.get("/api/v1/ai/risk-tasks", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_extract_tasks_returns_503_when_gemini_not_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None)
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)

    response = client.post(
        "/api/v1/ai/extract-tasks",
        json={"text": "Precisamos revisar o contrato até sexta.", "workspace_id": workspace_id},
        headers=headers,
    )
    assert response.status_code == 503


def test_extract_tasks_returns_502_when_key_has_non_ascii_characters(client, monkeypatch):
    # Guards against a real production incident: a mangled paste (e.g. a typographic dash swapped
    # in for a hyphen) corrupted the key, which crashed with an unhandled 500 deep inside httpx's
    # header encoding instead of a clean, actionable error.
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "sk-ant-api03-broken–key")
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)

    response = client.post(
        "/api/v1/ai/extract-tasks",
        json={"text": "Precisamos revisar o contrato até sexta.", "workspace_id": workspace_id},
        headers=headers,
    )
    assert response.status_code == 502
    assert "caracteres inválidos" in response.json()["detail"]


def test_extract_tasks_matches_project_and_normalizes_suggestions(client, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "fake-key-for-test")
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = create_project(client, headers, workspace_id, name="Logística Norte")

    def fake_extract(text, project_names, now=None):
        assert "Logística Norte" in project_names
        return [
            {
                "title": "Revisar contrato do fornecedor",
                "description": "Conferir cláusulas de reajuste",
                "priority": "P1",
                "due_date": "2026-08-01",
                "estimated_minutes": 60,
                "project_name": "Logística Norte",
            },
            {
                "title": "Sem projeto e prioridade inválida",
                "priority": "URGENTE",
                "project_name": "Projeto Que Não Existe",
            },
            {"title": ""},
        ]

    monkeypatch.setattr(ai_module, "extract_task_suggestions", fake_extract)

    response = client.post(
        "/api/v1/ai/extract-tasks",
        json={"text": "Ata de reunião de ontem...", "workspace_id": workspace_id},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2  # empty-title suggestion dropped

    first = body[0]
    assert first["title"] == "Revisar contrato do fornecedor"
    assert first["priority"] == "P1"
    assert first["due_date"] == "2026-08-01"
    assert first["estimated_minutes"] == 60
    assert first["suggested_project_id"] == project["id"]
    assert first["suggested_project_name"] == "Logística Norte"

    second = body[1]
    assert second["priority"] == "P4"  # invalid priority falls back to default
    assert second["suggested_project_id"] is None  # unmatched project name


def test_extract_tasks_requires_workspace_membership(client, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "fake-key-for-test")
    token_a = register_and_login(client, email="a@rbm.com")
    workspace_a = get_default_workspace_id(client, auth_headers(token_a))

    token_b = register_and_login(client, email="b@rbm.com")
    response = client.post(
        "/api/v1/ai/extract-tasks",
        json={"text": "Texto qualquer", "workspace_id": workspace_a},
        headers=auth_headers(token_b),
    )
    assert response.status_code == 404


def test_extract_tasks_rejects_empty_text(client, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "fake-key-for-test")
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)

    response = client.post(
        "/api/v1/ai/extract-tasks", json={"text": "", "workspace_id": workspace_id}, headers=headers
    )
    assert response.status_code == 422
