from tests.conftest import register_and_login, auth_headers, get_default_workspace_id


def test_register_creates_default_workspace(client):
    token = register_and_login(client)
    headers = auth_headers(token)

    response = client.get("/api/v1/workspaces/", headers=headers)
    assert response.status_code == 200
    workspaces = response.json()
    assert len(workspaces) == 1
    assert workspaces[0]["my_role"] == "owner"


def test_create_workspace(client):
    token = register_and_login(client)
    headers = auth_headers(token)

    response = client.post("/api/v1/workspaces/", json={"name": "Loja Online"}, headers=headers)
    assert response.status_code == 201
    assert response.json()["my_role"] == "owner"

    workspaces = client.get("/api/v1/workspaces/", headers=headers).json()
    assert len(workspaces) == 2


def test_owner_can_add_and_remove_member(client):
    owner_token = register_and_login(client, email="owner@rbm.com")
    owner_headers = auth_headers(owner_token)
    register_and_login(client, email="colleague@rbm.com")
    workspace_id = get_default_workspace_id(client, owner_headers)

    add = client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "colleague@rbm.com", "role": "member"},
        headers=owner_headers,
    )
    assert add.status_code == 201
    member_id = add.json()["id"]

    members = client.get(f"/api/v1/workspaces/{workspace_id}/members", headers=owner_headers).json()
    assert len(members) == 2

    remove = client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{member_id}", headers=owner_headers
    )
    assert remove.status_code == 204


def test_member_added_can_see_workspace_projects(client):
    owner_token = register_and_login(client, email="owner@rbm.com")
    owner_headers = auth_headers(owner_token)
    member_token = register_and_login(client, email="colleague@rbm.com")
    member_headers = auth_headers(member_token)
    workspace_id = get_default_workspace_id(client, owner_headers)

    client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "colleague@rbm.com", "role": "member"},
        headers=owner_headers,
    )

    project = client.post(
        "/api/v1/projects/", json={"name": "Projeto Compartilhado", "workspace_id": workspace_id},
        headers=owner_headers,
    ).json()

    listing = client.get(
        "/api/v1/projects/", params={"workspace_id": workspace_id}, headers=member_headers
    )
    assert listing.status_code == 200
    assert any(p["id"] == project["id"] for p in listing.json())


def test_non_member_cannot_see_workspace_projects(client):
    owner_token = register_and_login(client, email="owner@rbm.com")
    owner_headers = auth_headers(owner_token)
    outsider_token = register_and_login(client, email="outsider@rbm.com")
    outsider_headers = auth_headers(outsider_token)
    workspace_id = get_default_workspace_id(client, owner_headers)

    project = client.post(
        "/api/v1/projects/", json={"name": "Privado", "workspace_id": workspace_id},
        headers=owner_headers,
    ).json()

    response = client.get(f"/api/v1/projects/{project['id']}", headers=outsider_headers)
    assert response.status_code == 404

    listing = client.get(
        "/api/v1/projects/", params={"workspace_id": workspace_id}, headers=outsider_headers
    )
    assert listing.status_code == 404


def test_workspace_member_sees_all_tasks_in_project_board(client):
    owner_token = register_and_login(client, email="owner@rbm.com")
    owner_headers = auth_headers(owner_token)
    member_token = register_and_login(client, email="colleague@rbm.com")
    member_headers = auth_headers(member_token)
    workspace_id = get_default_workspace_id(client, owner_headers)

    client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "colleague@rbm.com", "role": "member"},
        headers=owner_headers,
    )
    project = client.post(
        "/api/v1/projects/", json={"name": "Projeto", "workspace_id": workspace_id},
        headers=owner_headers,
    ).json()
    task = client.post(
        "/api/v1/tasks/", json={"title": "Tarefa do owner", "project_id": project["id"]},
        headers=owner_headers,
    ).json()

    board = client.get(
        "/api/v1/tasks/board", params={"project_id": project["id"]}, headers=member_headers
    )
    assert board.status_code == 200
    assert any(t["id"] == task["id"] for t in board.json())

    detail = client.get(f"/api/v1/tasks/{task['id']}", headers=member_headers)
    assert detail.status_code == 200


def test_non_owner_cannot_delete_workspace(client):
    owner_token = register_and_login(client, email="owner@rbm.com")
    owner_headers = auth_headers(owner_token)
    member_token = register_and_login(client, email="colleague@rbm.com")
    member_headers = auth_headers(member_token)
    workspace_id = get_default_workspace_id(client, owner_headers)

    client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "colleague@rbm.com", "role": "admin"},
        headers=owner_headers,
    )

    response = client.delete(f"/api/v1/workspaces/{workspace_id}", headers=member_headers)
    assert response.status_code == 404
