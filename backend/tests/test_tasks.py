from tests.conftest import register_and_login, auth_headers


def _create_project(client, headers, name="Projeto"):
    return client.post("/api/v1/projects/", json={"name": name}, headers=headers).json()


def test_create_task_defaults_to_creator(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)

    response = client.post(
        "/api/v1/tasks/", json={"title": "Tarefa 1", "project_id": project["id"]}, headers=headers
    )
    assert response.status_code == 201
    task = response.json()
    assert task["assignee_id"] is not None
    assert task["priority"] == "P4"
    assert task["status"] == "todo"


def test_list_today_and_overdue(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)

    client.post(
        "/api/v1/tasks/",
        json={"title": "Atrasada", "project_id": project["id"], "due_date": "2000-01-01T00:00:00Z"},
        headers=headers,
    )

    overdue = client.get("/api/v1/tasks/overdue", headers=headers)
    assert overdue.status_code == 200
    assert len(overdue.json()) == 1


def test_update_task_marks_completed(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    task = client.post(
        "/api/v1/tasks/", json={"title": "T", "project_id": project["id"]}, headers=headers
    ).json()

    response = client.put(f"/api/v1/tasks/{task['id']}", json={"is_completed": True}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["is_completed"] is True
    assert body["completed_at"] is not None


def test_move_task_updates_status_and_board_order(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    task_a = client.post(
        "/api/v1/tasks/", json={"title": "A", "project_id": project["id"]}, headers=headers
    ).json()
    task_b = client.post(
        "/api/v1/tasks/", json={"title": "B", "project_id": project["id"]}, headers=headers
    ).json()

    move = client.patch(
        f"/api/v1/tasks/{task_a['id']}/move",
        json={"status": "in_progress", "position": 0},
        headers=headers,
    )
    assert move.status_code == 200
    assert move.json()["status"] == "in_progress"

    board = client.get(
        "/api/v1/tasks/board", params={"project_id": project["id"]}, headers=headers
    ).json()
    statuses = {t["id"]: t["status"] for t in board}
    assert statuses[task_a["id"]] == "in_progress"
    assert statuses[task_b["id"]] == "todo"


def test_subtasks_listed_under_parent(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    parent = client.post(
        "/api/v1/tasks/", json={"title": "Pai", "project_id": project["id"]}, headers=headers
    ).json()
    client.post(
        "/api/v1/tasks/",
        json={"title": "Filho", "project_id": project["id"], "parent_id": parent["id"]},
        headers=headers,
    )

    subtasks = client.get(f"/api/v1/tasks/{parent['id']}/subtasks", headers=headers)
    assert subtasks.status_code == 200
    assert len(subtasks.json()) == 1
    assert subtasks.json()[0]["title"] == "Filho"

    top_level = client.get("/api/v1/tasks/", headers=headers).json()
    assert all(t["id"] != subtasks.json()[0]["id"] for t in top_level)


def test_delete_task(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    task = client.post(
        "/api/v1/tasks/", json={"title": "Descartável", "project_id": project["id"]}, headers=headers
    ).json()

    response = client.delete(f"/api/v1/tasks/{task['id']}", headers=headers)
    assert response.status_code == 204
    assert client.get(f"/api/v1/tasks/{task['id']}", headers=headers).status_code == 404
