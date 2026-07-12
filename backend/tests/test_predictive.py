from datetime import datetime, timedelta, timezone
from tests.conftest import register_and_login, auth_headers, get_default_workspace_id, create_project


def _create_project(client, headers, workspace_id, name="P"):
    return create_project(client, headers, workspace_id, name=name)


def test_workload_requires_workspace_membership(client):
    token_a = register_and_login(client, email="a@rbm.com")
    token_b = register_and_login(client, email="b@rbm.com")
    workspace_a = get_default_workspace_id(client, auth_headers(token_a))

    response = client.get(
        f"/api/v1/predictive/workspaces/{workspace_a}/workload", headers=auth_headers(token_b)
    )
    assert response.status_code == 404


def test_workload_reflects_weighted_priority_load(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = _create_project(client, headers, workspace_id)

    client.post(
        "/api/v1/tasks", json={"title": "urgente", "project_id": project["id"], "priority": "P1"}, headers=headers
    )
    client.post(
        "/api/v1/tasks", json={"title": "baixa", "project_id": project["id"], "priority": "P4"}, headers=headers
    )

    response = client.get(f"/api/v1/predictive/workspaces/{workspace_id}/workload", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["active_task_count"] == 2
    assert body[0]["weighted_load"] == 5  # P1 (4) + P4 (1)
    assert body[0]["is_overloaded"] is False


def test_workload_does_not_leak_across_workspaces(client):
    token_a = register_and_login(client, email="a@rbm.com")
    headers_a = auth_headers(token_a)
    workspace_a = get_default_workspace_id(client, headers_a)
    project_a = _create_project(client, headers_a, workspace_a)
    client.post("/api/v1/tasks", json={"title": "t", "project_id": project_a["id"]}, headers=headers_a)

    token_b = register_and_login(client, email="b@rbm.com")
    headers_b = auth_headers(token_b)
    workspace_b = get_default_workspace_id(client, headers_b)

    response = client.get(f"/api/v1/predictive/workspaces/{workspace_b}/workload", headers=headers_b)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["active_task_count"] == 0


def test_project_risk_requires_access(client):
    token_a = register_and_login(client, email="a@rbm.com")
    headers_a = auth_headers(token_a)
    workspace_a = get_default_workspace_id(client, headers_a)
    project = _create_project(client, headers_a, workspace_a)

    token_b = register_and_login(client, email="b@rbm.com")
    response = client.get(f"/api/v1/predictive/projects/{project['id']}/risk", headers=auth_headers(token_b))
    assert response.status_code == 404


def test_project_risk_flags_overdue_tasks(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = _create_project(client, headers, workspace_id)

    past_due = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    client.post(
        "/api/v1/tasks",
        json={"title": "atrasada", "project_id": project["id"], "due_date": past_due},
        headers=headers,
    )

    response = client.get(f"/api/v1/predictive/projects/{project['id']}/risk", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_tasks"] == 1
    assert body["overdue"] == 1
    assert body["risk_score"] > 0
    assert body["level"] in ("low", "medium", "high")


def test_project_risk_empty_project_has_zero_score(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = _create_project(client, headers, workspace_id)

    response = client.get(f"/api/v1/predictive/projects/{project['id']}/risk", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_tasks"] == 0
    assert body["risk_score"] == 0
    assert body["level"] == "low"
