from datetime import datetime, timedelta, timezone
from tests.conftest import register_and_login, auth_headers, get_default_workspace_id, create_project


def test_admin_can_list_users_and_change_role(client):
    admin_token = register_and_login(client, email="admin@rbm.com")
    admin_headers = auth_headers(admin_token)
    register_and_login(client, email="member@rbm.com")

    listing = client.get("/api/v1/users", headers=admin_headers)
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

    response = client.get("/api/v1/users", headers=auth_headers(member_token))
    assert response.status_code == 403


def test_reports_xlsx_and_pdf_download(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = create_project(client, headers, workspace_id)
    client.post(
        "/api/v1/tasks", json={"title": "T", "project_id": project["id"]}, headers=headers
    )

    xlsx = client.get("/api/v1/reports/tasks.xlsx", headers=headers)
    assert xlsx.status_code == 200
    assert xlsx.headers["content-type"].startswith("application/vnd.openxmlformats")

    pdf = client.get("/api/v1/reports/tasks.pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"


def test_executive_report_returns_progress_and_status_breakdown(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = create_project(client, headers, workspace_id)
    task_a = client.post(
        "/api/v1/tasks", json={"title": "A", "project_id": project["id"]}, headers=headers
    ).json()
    client.post("/api/v1/tasks", json={"title": "B", "project_id": project["id"]}, headers=headers)
    client.put(f"/api/v1/tasks/{task_a['id']}", json={"is_completed": True}, headers=headers)

    response = client.get(f"/api/v1/reports/projects/{project['id']}/executive", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project["id"]
    assert body["total_tasks"] == 2
    assert body["completed_tasks"] == 1
    assert body["progress_percent"] == 50.0
    assert sum(row["count"] for row in body["status_breakdown"]) == 2
    assert "risk_level" in body


def test_executive_report_requires_project_access(client):
    token_a = register_and_login(client, email="a@rbm.com")
    headers_a = auth_headers(token_a)
    workspace_a = get_default_workspace_id(client, headers_a)
    project = create_project(client, headers_a, workspace_a)

    token_b = register_and_login(client, email="b@rbm.com")
    response = client.get(
        f"/api/v1/reports/projects/{project['id']}/executive", headers=auth_headers(token_b)
    )
    assert response.status_code == 404


def test_executive_report_pdf_download(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = create_project(client, headers, workspace_id)
    client.post("/api/v1/tasks", json={"title": "T", "project_id": project["id"]}, headers=headers)

    response = client.get(f"/api/v1/reports/projects/{project['id']}/executive.pdf", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_workspace_recap_counts_created_completed_overdue(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = create_project(client, headers, workspace_id)

    past_due = datetime.now(timezone.utc) - timedelta(days=1)
    overdue_task = client.post(
        "/api/v1/tasks",
        json={"title": "Atrasada", "project_id": project["id"], "due_date": past_due.isoformat()},
        headers=headers,
    ).json()
    done_task = client.post(
        "/api/v1/tasks", json={"title": "Feita", "project_id": project["id"]}, headers=headers
    ).json()
    client.put(f"/api/v1/tasks/{done_task['id']}", json={"is_completed": True}, headers=headers)

    response = client.get(
        f"/api/v1/reports/workspaces/{workspace_id}/recap", params={"period": "weekly"}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "weekly"
    assert body["tasks_created"] >= 2
    assert body["tasks_completed"] >= 1
    assert body["tasks_overdue"] >= 1
    assert any(c["completed_count"] >= 1 for c in body["top_contributors"])


def test_workspace_recap_rejects_invalid_period(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)

    response = client.get(
        f"/api/v1/reports/workspaces/{workspace_id}/recap", params={"period": "yearly"}, headers=headers
    )
    assert response.status_code == 400


def test_workspace_recap_requires_membership(client):
    token_a = register_and_login(client, email="a@rbm.com")
    workspace_a = get_default_workspace_id(client, auth_headers(token_a))

    token_b = register_and_login(client, email="b@rbm.com")
    response = client.get(
        f"/api/v1/reports/workspaces/{workspace_a}/recap", headers=auth_headers(token_b)
    )
    assert response.status_code == 404
