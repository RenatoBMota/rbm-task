from tests.conftest import register_and_login, auth_headers, get_default_workspace_id, create_project


def test_automation_rule_fires_notify_and_comment_on_task_created(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = create_project(client, headers, workspace_id)

    rule = client.post(
        "/api/v1/automations",
        json={
            "name": "Alerta P1",
            "trigger_event": "task_created",
            "conditions": {"priority": "P1"},
            "actions": [
                {"type": "notify_user", "message": "Urgente!"},
                {"type": "add_comment", "content": "Revisar com prioridade"},
            ],
        },
        headers=headers,
    )
    assert rule.status_code == 201
    rule_id = rule.json()["id"]

    task = client.post(
        "/api/v1/tasks",
        json={"title": "Urgente", "priority": "P1", "project_id": project["id"]},
        headers=headers,
    ).json()

    comments = client.get(f"/api/v1/tasks/{task['id']}/comments", headers=headers).json()
    assert any(c["content"] == "Revisar com prioridade" for c in comments)

    notifications = client.get("/api/v1/notifications", headers=headers).json()
    assert any(n["message"] == "Urgente!" for n in notifications)

    logs = client.get(f"/api/v1/automations/{rule_id}/logs", headers=headers).json()
    assert len(logs) == 2
    assert all(log["success"] for log in logs)


def test_automation_rule_does_not_fire_when_condition_mismatches(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = create_project(client, headers, workspace_id)

    rule = client.post(
        "/api/v1/automations",
        json={
            "name": "Alerta P1",
            "trigger_event": "task_created",
            "conditions": {"priority": "P1"},
            "actions": [{"type": "add_comment", "content": "Não deveria aparecer"}],
        },
        headers=headers,
    ).json()

    task = client.post(
        "/api/v1/tasks",
        json={"title": "Normal", "priority": "P4", "project_id": project["id"]},
        headers=headers,
    ).json()

    comments = client.get(f"/api/v1/tasks/{task['id']}/comments", headers=headers).json()
    assert comments == []

    logs = client.get(f"/api/v1/automations/{rule['id']}/logs", headers=headers).json()
    assert logs == []


def test_inactive_rule_toggle(client):
    token = register_and_login(client)
    headers = auth_headers(token)

    rule = client.post(
        "/api/v1/automations",
        json={"name": "R", "trigger_event": "task_created", "conditions": {}, "actions": []},
        headers=headers,
    ).json()

    disable = client.put(f"/api/v1/automations/{rule['id']}", json={"is_active": False}, headers=headers)
    assert disable.json()["is_active"] is False

    delete = client.delete(f"/api/v1/automations/{rule['id']}", headers=headers)
    assert delete.status_code == 204
