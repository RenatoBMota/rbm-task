from datetime import datetime, timedelta, timezone
from tests.conftest import register_and_login, auth_headers, get_default_workspace_id


def _create_project(client, headers, name="Projeto Gantt"):
    workspace_id = get_default_workspace_id(client, headers)
    return client.post(
        "/api/v1/projects", json={"name": name, "workspace_id": workspace_id}, headers=headers
    ).json()


def _create_task(client, headers, project_id, title, days_start=0, days_end=1, **overrides):
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    payload = {
        "title": title,
        "project_id": project_id,
        "start_date": (base + timedelta(days=days_start)).isoformat(),
        "due_date": (base + timedelta(days=days_end)).isoformat(),
        **overrides,
    }
    return client.post("/api/v1/tasks", json=payload, headers=headers).json()


def test_task_accepts_start_date_and_milestone(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)

    task = _create_task(client, headers, project["id"], "Marco", days_start=0, days_end=0, is_milestone=True)
    assert task["is_milestone"] is True
    assert task["start_date"] is not None


def test_dependency_persists_type_lag_hardness(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    a = _create_task(client, headers, project["id"], "A")
    b = _create_task(client, headers, project["id"], "B")

    response = client.post(
        f"/api/v1/tasks/{b['id']}/dependencies",
        json={"depends_on_id": a["id"], "dependency_type": "start_start", "lag_days": 2, "hardness": "rubber"},
        headers=headers,
    )
    assert response.status_code == 201
    dep = response.json()
    assert dep["dependency_type"] == "start_start"
    assert dep["lag_days"] == 2
    assert dep["hardness"] == "rubber"
    assert dep["task_id"] == b["id"]


def test_update_dependency(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    a = _create_task(client, headers, project["id"], "A")
    b = _create_task(client, headers, project["id"], "B")
    dep = client.post(
        f"/api/v1/tasks/{b['id']}/dependencies", json={"depends_on_id": a["id"]}, headers=headers
    ).json()

    response = client.put(
        f"/api/v1/tasks/{b['id']}/dependencies/{dep['id']}",
        json={"lag_days": 5, "hardness": "rubber"},
        headers=headers,
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["lag_days"] == 5
    assert updated["hardness"] == "rubber"
    assert updated["dependency_type"] == "finish_start"


def test_gantt_endpoint_returns_tasks_dependencies_and_critical_path(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)

    a = _create_task(client, headers, project["id"], "A", days_start=0, days_end=1)
    b = _create_task(client, headers, project["id"], "B", days_start=0, days_end=5)
    c = _create_task(client, headers, project["id"], "C", days_start=0, days_end=1)
    client.post(f"/api/v1/tasks/{b['id']}/dependencies", json={"depends_on_id": a["id"]}, headers=headers)
    client.post(f"/api/v1/tasks/{c['id']}/dependencies", json={"depends_on_id": a["id"]}, headers=headers)

    response = client.get(f"/api/v1/projects/{project['id']}/gantt", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["tasks"]) == 3
    assert len(body["dependencies"]) == 2
    assert a["id"] in body["critical_task_ids"]
    assert b["id"] in body["critical_task_ids"]
    assert c["id"] not in body["critical_task_ids"]


def test_gantt_endpoint_requires_project_access(client):
    token_a = register_and_login(client, email="a@rbm.com")
    headers_a = auth_headers(token_a)
    project = _create_project(client, headers_a)

    token_b = register_and_login(client, email="b@rbm.com")
    response = client.get(f"/api/v1/projects/{project['id']}/gantt", headers=auth_headers(token_b))
    assert response.status_code == 404


def test_gantt_endpoint_includes_subtasks(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    parent = _create_task(client, headers, project["id"], "Pai")
    child = client.post(
        "/api/v1/tasks",
        json={"title": "Filho", "project_id": project["id"], "parent_id": parent["id"]},
        headers=headers,
    ).json()

    response = client.get(f"/api/v1/projects/{project['id']}/gantt", headers=headers)
    task_ids = {t["id"] for t in response.json()["tasks"]}
    assert child["id"] in task_ids
