from datetime import datetime, timedelta, timezone
from app.core import scheduler as scheduler_module
from app.models.notification import Notification
from tests.conftest import register_and_login, auth_headers, get_default_workspace_id


def _create_project(client, headers, workspace_id, name="P"):
    return client.post(
        "/api/v1/projects", json={"name": name, "workspace_id": workspace_id}, headers=headers
    ).json()


def test_overload_alert_created_once_per_cooldown(client, db_session, monkeypatch):
    monkeypatch.setattr(scheduler_module, "SessionLocal", lambda: db_session)

    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = _create_project(client, headers, workspace_id)

    for i in range(4):
        client.post(
            "/api/v1/tasks",
            json={"title": f"t{i}", "project_id": project["id"], "priority": "P1"},
            headers=headers,
        )

    scheduler_module.check_team_overload_and_project_risk()
    overload = [n for n in db_session.query(Notification).all() if "sobrecarregado" in n.message]
    assert len(overload) == 1

    scheduler_module.check_team_overload_and_project_risk()
    overload_after = [n for n in db_session.query(Notification).all() if "sobrecarregado" in n.message]
    assert len(overload_after) == 1


def test_no_overload_alert_below_threshold(client, db_session, monkeypatch):
    monkeypatch.setattr(scheduler_module, "SessionLocal", lambda: db_session)

    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = _create_project(client, headers, workspace_id)
    client.post(
        "/api/v1/tasks", json={"title": "t", "project_id": project["id"], "priority": "P4"}, headers=headers
    )

    scheduler_module.check_team_overload_and_project_risk()
    assert db_session.query(Notification).count() == 0


def test_project_risk_alert_created_for_high_risk_project(client, db_session, monkeypatch):
    monkeypatch.setattr(scheduler_module, "SessionLocal", lambda: db_session)

    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    project = _create_project(client, headers, workspace_id)

    past_due = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    client.post(
        "/api/v1/tasks",
        json={"title": "atrasada", "project_id": project["id"], "due_date": past_due},
        headers=headers,
    )

    scheduler_module.check_team_overload_and_project_risk()
    risk_alerts = [n for n in db_session.query(Notification).all() if "risco alto" in n.message]
    assert len(risk_alerts) == 1
