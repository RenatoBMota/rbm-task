from datetime import datetime, timedelta, timezone
from tests.conftest import register_and_login, auth_headers, get_default_workspace_id, create_project


def _create_project(client, headers, workspace_id, name="P"):
    return create_project(client, headers, workspace_id, name=name)


def test_create_and_list_resources(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)

    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/resources",
        json={"name": "Ana", "role": "Developer", "standard_rate": 500},
        headers=headers,
    )
    assert response.status_code == 201
    resource = response.json()
    assert resource["name"] == "Ana"
    assert resource["standard_rate"] == 500

    listed = client.get(f"/api/v1/workspaces/{workspace_id}/resources", headers=headers).json()
    assert len(listed) == 1


def test_resources_require_workspace_membership(client):
    token_a = register_and_login(client, email="a@rbm.com")
    workspace_a = get_default_workspace_id(client, auth_headers(token_a))

    token_b = register_and_login(client, email="b@rbm.com")
    response = client.post(
        f"/api/v1/workspaces/{workspace_a}/resources",
        json={"name": "Intruder"},
        headers=auth_headers(token_b),
    )
    assert response.status_code == 404


def test_assign_resource_to_task_and_update_allocation(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = _create_project(client, headers, workspace_id)
    resource = client.post(
        f"/api/v1/workspaces/{workspace_id}/resources",
        json={"name": "Bruno", "standard_rate": 300},
        headers=headers,
    ).json()
    task = client.post(
        "/api/v1/tasks", json={"title": "T", "project_id": project["id"]}, headers=headers
    ).json()

    response = client.post(
        f"/api/v1/tasks/{task['id']}/resources",
        json={"resource_id": resource["id"], "allocation_percent": 50},
        headers=headers,
    )
    assert response.status_code == 201
    assignment = response.json()
    assert assignment["allocation_percent"] == 50
    assert assignment["resource_name"] == "Bruno"

    updated = client.put(
        f"/api/v1/tasks/{task['id']}/resources/{assignment['id']}",
        json={"allocation_percent": 80, "is_coordinator": True},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["allocation_percent"] == 80
    assert updated.json()["is_coordinator"] is True

    listed = client.get(f"/api/v1/tasks/{task['id']}/resources", headers=headers).json()
    assert len(listed) == 1

    delete_resp = client.delete(
        f"/api/v1/tasks/{task['id']}/resources/{assignment['id']}", headers=headers
    )
    assert delete_resp.status_code == 204
    assert client.get(f"/api/v1/tasks/{task['id']}/resources", headers=headers).json() == []


def test_gantt_task_cost_reflects_duration_rate_and_allocation(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = _create_project(client, headers, workspace_id)
    resource = client.post(
        f"/api/v1/workspaces/{workspace_id}/resources",
        json={"name": "Carla", "standard_rate": 200},
        headers=headers,
    ).json()

    base = datetime.now(timezone.utc) + timedelta(days=1)
    task = client.post(
        "/api/v1/tasks",
        json={
            "title": "T",
            "project_id": project["id"],
            "start_date": base.isoformat(),
            "due_date": (base + timedelta(days=5)).isoformat(),
        },
        headers=headers,
    ).json()
    client.post(
        f"/api/v1/tasks/{task['id']}/resources",
        json={"resource_id": resource["id"], "allocation_percent": 50},
        headers=headers,
    )

    gantt = client.get(f"/api/v1/projects/{project['id']}/gantt", headers=headers).json()
    # 5 days * 200/day * 50% = 500
    assert gantt["task_costs"][str(task["id"])] == 500.0


def test_resource_utilization_counts_active_assignments(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = _create_project(client, headers, workspace_id)
    resource = client.post(
        f"/api/v1/workspaces/{workspace_id}/resources", json={"name": "Diego"}, headers=headers
    ).json()

    now = datetime.now(timezone.utc)
    task = client.post(
        "/api/v1/tasks",
        json={
            "title": "Ativa",
            "project_id": project["id"],
            "start_date": (now - timedelta(days=1)).isoformat(),
            "due_date": (now + timedelta(days=1)).isoformat(),
        },
        headers=headers,
    ).json()
    client.post(
        f"/api/v1/tasks/{task['id']}/resources",
        json={"resource_id": resource["id"], "allocation_percent": 60},
        headers=headers,
    )

    response = client.get(f"/api/v1/workspaces/{workspace_id}/resources/utilization", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body[0]["total_allocation_percent"] == 60
    assert body[0]["task_count"] == 1
