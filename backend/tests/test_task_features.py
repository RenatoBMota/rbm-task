from datetime import datetime, timedelta, timezone
from tests.conftest import register_and_login, auth_headers, get_default_workspace_id, create_project


def _create_project(client, headers, name="P"):
    workspace_id = get_default_workspace_id(client, headers)
    return create_project(client, headers, workspace_id, name=name)


def test_completing_recurring_task_creates_next_occurrence(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    due_date = datetime.now(timezone.utc) + timedelta(days=5)
    task = client.post(
        "/api/v1/tasks",
        json={
            "title": "Reunião semanal", "project_id": project["id"],
            "due_date": due_date.isoformat(), "recurrence": "weekly",
        },
        headers=headers,
    ).json()

    client.put(f"/api/v1/tasks/{task['id']}", json={"is_completed": True}, headers=headers)

    all_tasks = client.get(
        "/api/v1/tasks", params={"project_id": project["id"]}, headers=headers
    ).json()
    titles = [t["title"] for t in all_tasks]
    assert titles.count("Reunião semanal") == 2
    next_occurrence = next(t for t in all_tasks if not t["is_completed"])
    next_due = due_date + timedelta(weeks=1)
    assert next_occurrence["due_date"].startswith(next_due.date().isoformat())


def test_task_history_records_status_change(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    task = client.post(
        "/api/v1/tasks", json={"title": "T", "project_id": project["id"]}, headers=headers
    ).json()

    client.patch(
        f"/api/v1/tasks/{task['id']}/move", json={"status": "in_progress", "position": 0}, headers=headers
    )

    history = client.get(f"/api/v1/tasks/{task['id']}/history", headers=headers).json()
    assert any(h["field_name"] == "status" and h["new_value"] == "in_progress" for h in history)


def test_task_with_incomplete_dependency_can_still_be_moved_freely(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    blocker = client.post(
        "/api/v1/tasks", json={"title": "Bloqueadora", "project_id": project["id"]}, headers=headers
    ).json()
    task = client.post(
        "/api/v1/tasks", json={"title": "Bloqueada", "project_id": project["id"]}, headers=headers
    ).json()

    client.post(
        f"/api/v1/tasks/{task['id']}/dependencies",
        json={"depends_on_id": blocker["id"]},
        headers=headers,
    )

    # Dependencies are informational (used for Gantt scheduling) and no longer
    # gate Kanban drag-and-drop: the blocker is still incomplete, but the move succeeds.
    response = client.patch(
        f"/api/v1/tasks/{task['id']}/move", json={"status": "done", "position": 0}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "done"


def test_marking_task_completed_moves_status_to_done_on_kanban(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    task = client.post(
        "/api/v1/tasks", json={"title": "T", "project_id": project["id"]}, headers=headers
    ).json()
    client.patch(
        f"/api/v1/tasks/{task['id']}/move", json={"status": "in_progress", "position": 0}, headers=headers
    )

    response = client.put(f"/api/v1/tasks/{task['id']}", json={"is_completed": True}, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "done"

    board = client.get(
        "/api/v1/tasks/board", params={"project_id": project["id"]}, headers=headers
    ).json()
    done_task = next(t for t in board if t["id"] == task["id"])
    assert done_task["status"] == "done"

    uncompleted = client.put(f"/api/v1/tasks/{task['id']}", json={"is_completed": False}, headers=headers)
    assert uncompleted.json()["status"] == "todo"


def test_moving_task_to_done_column_marks_it_completed(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    task = client.post(
        "/api/v1/tasks", json={"title": "T", "project_id": project["id"]}, headers=headers
    ).json()

    response = client.patch(
        f"/api/v1/tasks/{task['id']}/move", json={"status": "done", "position": 0}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["is_completed"] is True
    assert response.json()["completed_at"] is not None

    moved_back = client.patch(
        f"/api/v1/tasks/{task['id']}/move", json={"status": "in_progress", "position": 0}, headers=headers
    )
    assert moved_back.json()["is_completed"] is False
    assert moved_back.json()["completed_at"] is None


def test_duplicate_project_copies_tasks_as_template(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers, name="Original")
    client.post(
        "/api/v1/tasks",
        json={"title": "Passo 1", "project_id": project["id"], "priority": "P2"},
        headers=headers,
    )

    duplicate = client.post(
        f"/api/v1/projects/{project['id']}/duplicate", json={"name": "Cópia"}, headers=headers
    )
    assert duplicate.status_code == 201
    new_project = duplicate.json()

    tasks = client.get(
        "/api/v1/tasks", params={"project_id": new_project["id"]}, headers=headers
    ).json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Passo 1"
    assert tasks[0]["status"] == "todo"


def test_labels_attach_and_detach(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    task = client.post(
        "/api/v1/tasks", json={"title": "T", "project_id": project["id"]}, headers=headers
    ).json()
    label = client.post(
        "/api/v1/labels", json={"name": "Urgente", "color": "#ff0000"}, headers=headers
    ).json()

    attach = client.post(f"/api/v1/tasks/{task['id']}/labels/{label['id']}", headers=headers)
    assert attach.status_code == 200
    assert any(l["id"] == label["id"] for l in attach.json()["labels"])

    detach = client.delete(f"/api/v1/tasks/{task['id']}/labels/{label['id']}", headers=headers)
    assert detach.json()["labels"] == []


def test_task_reminders_lifecycle(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    task = client.post(
        "/api/v1/tasks", json={"title": "T", "project_id": project["id"]}, headers=headers
    ).json()

    create = client.post(
        f"/api/v1/tasks/{task['id']}/reminders",
        json={"remind_at": "2026-01-01T09:00:00Z"},
        headers=headers,
    )
    assert create.status_code == 201
    reminder_id = create.json()["id"]

    listing = client.get(f"/api/v1/tasks/{task['id']}/reminders", headers=headers).json()
    assert len(listing) == 1

    delete = client.delete(f"/api/v1/tasks/{task['id']}/reminders/{reminder_id}", headers=headers)
    assert delete.status_code == 204


def test_duplicate_and_archive_task(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = _create_project(client, headers)
    task = client.post(
        "/api/v1/tasks", json={"title": "Original", "project_id": project["id"]}, headers=headers
    ).json()

    duplicate = client.post(f"/api/v1/tasks/{task['id']}/duplicate", json={}, headers=headers)
    assert duplicate.status_code == 201
    assert duplicate.json()["title"] == "Original (cópia)"

    archive = client.put(f"/api/v1/tasks/{task['id']}", json={"is_archived": True}, headers=headers)
    assert archive.json()["is_archived"] is True
