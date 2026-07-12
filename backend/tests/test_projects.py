from tests.conftest import register_and_login, auth_headers, get_default_workspace_id


def test_create_and_list_project(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)

    create = client.post(
        "/api/v1/projects", json={"name": "Projeto A", "workspace_id": workspace_id}, headers=headers
    )
    assert create.status_code == 201
    project_id = create.json()["id"]

    listing = client.get("/api/v1/projects", params={"workspace_id": workspace_id}, headers=headers)
    assert listing.status_code == 200
    assert any(p["id"] == project_id for p in listing.json())


def test_update_project(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = client.post(
        "/api/v1/projects", json={"name": "Original", "workspace_id": workspace_id}, headers=headers
    ).json()

    response = client.put(
        f"/api/v1/projects/{project['id']}", json={"name": "Atualizado"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Atualizado"


def test_delete_project(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = client.post(
        "/api/v1/projects", json={"name": "Descartável", "workspace_id": workspace_id}, headers=headers
    ).json()

    response = client.delete(f"/api/v1/projects/{project['id']}", headers=headers)
    assert response.status_code == 204

    listing = client.get("/api/v1/projects", params={"workspace_id": workspace_id}, headers=headers)
    assert all(p["id"] != project["id"] for p in listing.json())
