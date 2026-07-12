from tests.conftest import register_and_login, auth_headers


def test_create_and_list_project(client):
    token = register_and_login(client)
    headers = auth_headers(token)

    create = client.post("/api/v1/projects/", json={"name": "Projeto A"}, headers=headers)
    assert create.status_code == 201
    project_id = create.json()["id"]

    listing = client.get("/api/v1/projects/", headers=headers)
    assert listing.status_code == 200
    assert any(p["id"] == project_id for p in listing.json())


def test_update_project(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = client.post("/api/v1/projects/", json={"name": "Original"}, headers=headers).json()

    response = client.put(
        f"/api/v1/projects/{project['id']}", json={"name": "Atualizado"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Atualizado"


def test_delete_project(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    project = client.post("/api/v1/projects/", json={"name": "Descartável"}, headers=headers).json()

    response = client.delete(f"/api/v1/projects/{project['id']}", headers=headers)
    assert response.status_code == 204

    listing = client.get("/api/v1/projects/", headers=headers)
    assert all(p["id"] != project["id"] for p in listing.json())
