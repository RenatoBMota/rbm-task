from tests.conftest import register_and_login, auth_headers, get_default_workspace_id


def test_admin_can_list_users_and_change_role(client):
    admin_token = register_and_login(client, email="admin@rbm.com")
    admin_headers = auth_headers(admin_token)
    register_and_login(client, email="member@rbm.com")

    listing = client.get("/api/v1/users/", headers=admin_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 2

    member = next(u for u in listing.json() if u["email"] == "member@rbm.com")
    promote = client.put(
        f"/api/v1/users/{member['id']}/role", json={"role": "admin"}, headers=admin_headers
    )
    assert promote.status_code == 200
    assert promote.json()["role"] == "admin"


def test_member_cannot_list_users(client):
    register_and_login(client, email="admin@rbm.com")
    member_token = register_and_login(client, email="member@rbm.com")

    response = client.get("/api/v1/users/", headers=auth_headers(member_token))
    assert response.status_code == 403


def test_reports_xlsx_and_pdf_download(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = client.post(
        "/api/v1/projects/", json={"name": "P", "workspace_id": workspace_id}, headers=headers
    ).json()
    client.post(
        "/api/v1/tasks/", json={"title": "T", "project_id": project["id"]}, headers=headers
    )

    xlsx = client.get("/api/v1/reports/tasks.xlsx", headers=headers)
    assert xlsx.status_code == 200
    assert xlsx.headers["content-type"].startswith("application/vnd.openxmlformats")

    pdf = client.get("/api/v1/reports/tasks.pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
