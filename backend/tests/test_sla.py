from tests.conftest import register_and_login, auth_headers, get_default_workspace_id


def test_default_sla_policies_returned(client):
    token = register_and_login(client)
    headers = auth_headers(token)

    response = client.get("/api/v1/sla-policies/", headers=headers)
    assert response.status_code == 200
    policies = {p["priority"]: p["target_hours"] for p in response.json()}
    assert policies == {"P1": 4, "P2": 24, "P3": 72, "P4": 168}


def test_admin_can_update_sla_policy(client):
    token = register_and_login(client)
    headers = auth_headers(token)

    response = client.put("/api/v1/sla-policies/P1", json={"target_hours": 2}, headers=headers)
    assert response.status_code == 200
    assert response.json()["target_hours"] == 2


def test_member_cannot_update_sla_policy(client):
    register_and_login(client, email="admin@rbm.com")
    member_token = register_and_login(client, email="member@rbm.com")
    headers = auth_headers(member_token)

    response = client.put("/api/v1/sla-policies/P1", json={"target_hours": 2}, headers=headers)
    assert response.status_code == 403


def test_task_sla_status_on_time_without_due_date(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = client.post(
        "/api/v1/projects/", json={"name": "P", "workspace_id": workspace_id}, headers=headers
    ).json()
    task = client.post(
        "/api/v1/tasks/", json={"title": "T", "project_id": project["id"]}, headers=headers
    ).json()

    response = client.get(f"/api/v1/tasks/{task['id']}/sla/", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "on_time"
