from datetime import datetime, timedelta, timezone
from tests.conftest import register_and_login, auth_headers, get_default_workspace_id, create_project


def test_create_project_requires_start_and_end_dates(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)

    response = client.post(
        "/api/v1/projects", json={"name": "Sem datas", "workspace_id": workspace_id}, headers=headers
    )
    assert response.status_code == 422


def test_create_project_rejects_end_before_start(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    now = datetime.now(timezone.utc)

    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Datas invertidas",
            "workspace_id": workspace_id,
            "start_date": now.isoformat(),
            "end_date": (now - timedelta(days=1)).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_create_and_list_project(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)

    project = create_project(client, headers, workspace_id, name="Projeto A")
    assert project["start_date"] is not None
    assert project["end_date"] is not None

    listing = client.get("/api/v1/projects", params={"workspace_id": workspace_id}, headers=headers)
    assert listing.status_code == 200
    assert any(p["id"] == project["id"] for p in listing.json())


def test_update_project_name(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = create_project(client, headers, workspace_id, name="Original")

    response = client.put(
        f"/api/v1/projects/{project['id']}", json={"name": "Atualizado"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Atualizado"


def test_update_project_can_extend_duration(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = create_project(client, headers, workspace_id)
    new_end = datetime.fromisoformat(project["end_date"]) + timedelta(days=30)

    response = client.put(
        f"/api/v1/projects/{project['id']}", json={"end_date": new_end.isoformat()}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["end_date"] == new_end.isoformat()


def test_update_project_blocks_shrink_past_existing_task_dates(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = create_project(client, headers, workspace_id)
    task_due = datetime.now(timezone.utc) + timedelta(days=100)
    client.post(
        "/api/v1/tasks",
        json={"title": "T", "project_id": project["id"], "due_date": task_due.isoformat()},
        headers=headers,
    )

    response = client.put(
        f"/api/v1/projects/{project['id']}",
        json={"end_date": (task_due - timedelta(days=5)).isoformat()},
        headers=headers,
    )
    assert response.status_code == 400


def test_delete_project(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = create_project(client, headers, workspace_id, name="Descartável")

    response = client.delete(f"/api/v1/projects/{project['id']}", headers=headers)
    assert response.status_code == 204

    listing = client.get("/api/v1/projects", params={"workspace_id": workspace_id}, headers=headers)
    assert all(p["id"] != project["id"] for p in listing.json())


def test_task_date_outside_project_range_is_rejected(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    now = datetime.now(timezone.utc)
    project = create_project(
        client, headers, workspace_id,
        start_date=now.isoformat(), end_date=(now + timedelta(days=10)).isoformat(),
    )

    response = client.post(
        "/api/v1/tasks",
        json={
            "title": "Fora do prazo",
            "project_id": project["id"],
            "due_date": (now + timedelta(days=20)).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 400


def test_task_date_within_project_range_succeeds(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    now = datetime.now(timezone.utc)
    project = create_project(
        client, headers, workspace_id,
        start_date=now.isoformat(), end_date=(now + timedelta(days=10)).isoformat(),
    )

    response = client.post(
        "/api/v1/tasks",
        json={
            "title": "Dentro do prazo",
            "project_id": project["id"],
            "due_date": (now + timedelta(days=5)).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 201
