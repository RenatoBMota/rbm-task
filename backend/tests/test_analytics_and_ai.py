from tests.conftest import register_and_login, auth_headers, get_default_workspace_id


def _create_task(client, headers, **overrides):
    workspace_id = get_default_workspace_id(client, headers)
    project = client.post(
        "/api/v1/projects", json={"name": "P", "workspace_id": workspace_id}, headers=headers
    ).json()
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
