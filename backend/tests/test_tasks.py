from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from tests.conftest import register_and_login, auth_headers, get_default_workspace_id, create_project

BUSINESS_TZ = ZoneInfo("America/Sao_Paulo")


def _create_project(client, headers, name="Projeto"):
    workspace_id = get_default_workspace_id(client, headers)
    return create_project(client, headers, workspace_id, name=name)


def test_create_task_defaults_to_creator(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)

    response = client.post(
        "/api/v1/tasks", json={"title": "Tarefa 1", "project_id": project["id"]}, headers=headers
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

    overdue_date = datetime.now(timezone.utc) - timedelta(days=1)
    client.post(
        "/api/v1/tasks",
        json={"title": "Atrasada", "project_id": project["id"], "due_date": overdue_date.isoformat()},
        headers=headers,
    )

    overdue = client.get("/api/v1/tasks/overdue", headers=headers)
    assert overdue.status_code == 200
    assert len(overdue.json()) == 1


def test_today_tasks_use_brazil_calendar_day_not_utc(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)

    now_brt = datetime.now(BUSINESS_TZ)
    # Due late tonight in Brazil time — this can already be tomorrow in UTC
    # (e.g. 23:30 BRT = 02:30 UTC the next day), which is exactly the case
    # that must still count as "today" for a Brazil-based user.
    due_tonight_brt = now_brt.replace(hour=23, minute=30, second=0, microsecond=0)
    client.post(
        "/api/v1/tasks",
        json={"title": "Hoje à noite", "project_id": project["id"], "due_date": due_tonight_brt.isoformat()},
        headers=headers,
    )

    today = client.get("/api/v1/tasks/today", headers=headers)
    assert today.status_code == 200
    assert any(t["title"] == "Hoje à noite" for t in today.json())


def test_update_task_marks_completed(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    task = client.post(
        "/api/v1/tasks", json={"title": "T", "project_id": project["id"]}, headers=headers
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
        "/api/v1/tasks", json={"title": "A", "project_id": project["id"]}, headers=headers
    ).json()
    task_b = client.post(
        "/api/v1/tasks", json={"title": "B", "project_id": project["id"]}, headers=headers
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


def test_board_without_project_returns_standalone_tasks_for_current_user(client):
    token_a = register_and_login(client, email="a@rbm.com")
    headers_a = auth_headers(token_a)
    token_b = register_and_login(client, email="b@rbm.com")
    headers_b = auth_headers(token_b)

    client.post("/api/v1/tasks", json={"title": "Agenda A"}, headers=headers_a)
    client.post("/api/v1/tasks", json={"title": "Agenda B"}, headers=headers_b)

    board = client.get("/api/v1/tasks/board", headers=headers_a)
    assert board.status_code == 200
    titles = [t["title"] for t in board.json()]
    assert titles == ["Agenda A"]


def test_subtasks_listed_under_parent(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    parent = client.post(
        "/api/v1/tasks", json={"title": "Pai", "project_id": project["id"]}, headers=headers
    ).json()
    client.post(
        "/api/v1/tasks",
        json={"title": "Filho", "project_id": project["id"], "parent_id": parent["id"]},
        headers=headers,
    )

    subtasks = client.get(f"/api/v1/tasks/{parent['id']}/subtasks", headers=headers)
    assert subtasks.status_code == 200
    assert len(subtasks.json()) == 1
    assert subtasks.json()[0]["title"] == "Filho"

    top_level = client.get("/api/v1/tasks", headers=headers).json()
    assert all(t["id"] != subtasks.json()[0]["id"] for t in top_level)


def test_delete_task(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    task = client.post(
        "/api/v1/tasks", json={"title": "Descartável", "project_id": project["id"]}, headers=headers
    ).json()

    response = client.delete(f"/api/v1/tasks/{task['id']}", headers=headers)
    assert response.status_code == 204
    assert client.get(f"/api/v1/tasks/{task['id']}", headers=headers).status_code == 404


def test_delete_task_with_notification_dependents_and_subtasks(client):
    """Regression test: deleting a task used to raise a FK IntegrityError (500) in
    Postgres when a notification referenced it, another task depended on it, or it
    had subtasks. SQLite doesn't enforce FK constraints so this only exercises the
    ORM-level cascade paths; the ON DELETE SET NULL/CASCADE behavior itself was
    verified live against Postgres.
    """
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    me = client.get("/api/v1/users/me", headers=headers).json()

    task = client.post(
        "/api/v1/tasks",
        json={"title": "teste", "project_id": project["id"], "assignee_id": me["id"]},
        headers=headers,
    ).json()
    dependent = client.post(
        "/api/v1/tasks", json={"title": "depende", "project_id": project["id"]}, headers=headers
    ).json()
    client.post(
        f"/api/v1/tasks/{dependent['id']}/dependencies", json={"depends_on_id": task["id"]}, headers=headers
    )
    subtask = client.post(
        "/api/v1/tasks",
        json={"title": "subtarefa", "project_id": project["id"], "parent_id": task["id"]},
        headers=headers,
    ).json()

    response = client.delete(f"/api/v1/tasks/{task['id']}", headers=headers)
    assert response.status_code == 204
    assert client.get(f"/api/v1/tasks/{dependent['id']}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/tasks/{subtask['id']}", headers=headers).status_code == 404


def test_list_tasks_scoped_to_workspace_includes_personal_tasks(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_a = get_default_workspace_id(client, headers)
    project_a = _create_project(client, headers, name="Projeto A")

    workspace_b = client.post(
        "/api/v1/workspaces", json={"name": "Segunda área"}, headers=headers
    ).json()["id"]
    project_b = create_project(client, headers, workspace_b, name="Projeto B")

    client.post("/api/v1/tasks", json={"title": "Tarefa A", "project_id": project_a["id"]}, headers=headers)
    client.post("/api/v1/tasks", json={"title": "Tarefa B", "project_id": project_b["id"]}, headers=headers)
    client.post("/api/v1/tasks", json={"title": "Tarefa pessoal"}, headers=headers)

    response = client.get("/api/v1/tasks", params={"workspace_id": workspace_a}, headers=headers)
    assert response.status_code == 200
    titles = {t["title"] for t in response.json()}
    assert titles == {"Tarefa A", "Tarefa pessoal"}


def test_list_tasks_requires_workspace_membership(client):
    token_a = register_and_login(client, email="a@rbm.com")
    token_b = register_and_login(client, email="b@rbm.com")
    workspace_a = get_default_workspace_id(client, auth_headers(token_a))

    response = client.get(
        "/api/v1/tasks", params={"workspace_id": workspace_a}, headers=auth_headers(token_b)
    )
    assert response.status_code == 404
