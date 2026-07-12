from tests.conftest import register_and_login, auth_headers, get_default_workspace_id


def _create_task(client, headers):
    workspace_id = get_default_workspace_id(client, headers)
    project = client.post(
        "/api/v1/projects", json={"name": "P", "workspace_id": workspace_id}, headers=headers
    ).json()
    return client.post(
        "/api/v1/tasks", json={"title": "T", "project_id": project["id"]}, headers=headers
    ).json()


def test_checklist_item_lifecycle(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    task = _create_task(client, headers)

    create = client.post(
        f"/api/v1/tasks/{task['id']}/checklist", json={"title": "Item 1"}, headers=headers
    )
    assert create.status_code == 201
    item = create.json()
    assert item["is_completed"] is False

    toggle = client.put(
        f"/api/v1/tasks/{task['id']}/checklist/{item['id']}",
        json={"is_completed": True},
        headers=headers,
    )
    assert toggle.json()["is_completed"] is True

    delete = client.delete(f"/api/v1/tasks/{task['id']}/checklist/{item['id']}", headers=headers)
    assert delete.status_code == 204

    listing = client.get(f"/api/v1/tasks/{task['id']}/checklist", headers=headers)
    assert listing.json() == []


def test_comment_with_mention_notifies_mentioned_user(client):
    token = register_and_login(client, email="author@rbm.com")
    headers = auth_headers(token)
    client.post(
        "/api/v1/auth/register",
        json={"email": "mentioned@rbm.com", "full_name": "Mentioned", "password": "senha123"},
    )
    task = _create_task(client, headers)

    comment = client.post(
        f"/api/v1/tasks/{task['id']}/comments",
        json={"content": "Olha isso @mentioned@rbm.com"},
        headers=headers,
    )
    assert comment.status_code == 201

    mentioned_login = client.post(
        "/api/v1/auth/login", json={"email": "mentioned@rbm.com", "password": "senha123"}
    )
    mentioned_headers = auth_headers(mentioned_login.json()["access_token"])
    notifications = client.get("/api/v1/notifications", headers=mentioned_headers).json()
    assert any(n["type"] == "comment_mention" for n in notifications)
