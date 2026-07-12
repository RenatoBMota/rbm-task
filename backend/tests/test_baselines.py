from datetime import datetime, timedelta, timezone
from tests.conftest import register_and_login, auth_headers, get_default_workspace_id


def _create_project(client, headers, workspace_id, name="P"):
    return client.post(
        "/api/v1/projects", json={"name": name, "workspace_id": workspace_id}, headers=headers
    ).json()


def test_create_baseline_snapshots_task_dates(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = _create_project(client, headers, workspace_id)

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    task = client.post(
        "/api/v1/tasks",
        json={
            "title": "T",
            "project_id": project["id"],
            "start_date": base.isoformat(),
            "due_date": (base + timedelta(days=3)).isoformat(),
        },
        headers=headers,
    ).json()

    response = client.post(
        f"/api/v1/projects/{project['id']}/baselines", json={"name": "V1"}, headers=headers
    )
    assert response.status_code == 201
    baseline = response.json()
    assert baseline["name"] == "V1"
    assert len(baseline["tasks"]) == 1
    assert baseline["tasks"][0]["task_id"] == task["id"]
    assert baseline["tasks"][0]["due_date"] is not None

    # rescheduling the task afterwards must not affect the stored baseline snapshot
    client.put(
        f"/api/v1/tasks/{task['id']}",
        json={"due_date": (base + timedelta(days=10)).isoformat()},
        headers=headers,
    )
    refetched = client.get(
        f"/api/v1/projects/{project['id']}/baselines/{baseline['id']}", headers=headers
    ).json()
    assert refetched["tasks"][0]["due_date"] == baseline["tasks"][0]["due_date"]


def test_list_and_delete_baselines(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = _create_project(client, headers, workspace_id)

    b1 = client.post(f"/api/v1/projects/{project['id']}/baselines", json={"name": "V1"}, headers=headers).json()
    client.post(f"/api/v1/projects/{project['id']}/baselines", json={"name": "V2"}, headers=headers)

    listed = client.get(f"/api/v1/projects/{project['id']}/baselines", headers=headers).json()
    assert len(listed) == 2

    delete_resp = client.delete(f"/api/v1/projects/{project['id']}/baselines/{b1['id']}", headers=headers)
    assert delete_resp.status_code == 204
    assert len(client.get(f"/api/v1/projects/{project['id']}/baselines", headers=headers).json()) == 1


def test_baselines_require_project_access(client):
    token_a = register_and_login(client, email="a@rbm.com")
    headers_a = auth_headers(token_a)
    workspace_a = get_default_workspace_id(client, headers_a)
    project = _create_project(client, headers_a, workspace_a)

    token_b = register_and_login(client, email="b@rbm.com")
    response = client.post(
        f"/api/v1/projects/{project['id']}/baselines", json={"name": "X"}, headers=auth_headers(token_b)
    )
    assert response.status_code == 404


def test_deleting_task_does_not_break_existing_baseline(client):
    # Note: the FK from gantt_baseline_tasks.task_id to tasks.id is declared
    # ON DELETE SET NULL so old baselines survive a task being deleted later.
    # SQLite (used here) doesn't enforce FK actions without a pragma this
    # fixture doesn't set, so this only exercises that the delete itself
    # doesn't error — the actual SET NULL behavior is verified against
    # Postgres directly (see migration validation notes).
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = _create_project(client, headers, workspace_id)
    task = client.post(
        "/api/v1/tasks", json={"title": "T", "project_id": project["id"]}, headers=headers
    ).json()
    baseline = client.post(
        f"/api/v1/projects/{project['id']}/baselines", json={"name": "V1"}, headers=headers
    ).json()

    delete_resp = client.delete(f"/api/v1/tasks/{task['id']}", headers=headers)
    assert delete_resp.status_code == 204

    refetched = client.get(
        f"/api/v1/projects/{project['id']}/baselines/{baseline['id']}", headers=headers
    )
    assert refetched.status_code == 200
    assert refetched.json()["tasks"][0]["title"] == "T"
