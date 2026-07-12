from datetime import datetime, timedelta, timezone
from tests.conftest import register_and_login, auth_headers, get_default_workspace_id

API = "/api/v1/okr"


def create_objective(client, headers, workspace_id, **overrides):
    now = datetime.now(timezone.utc)
    payload = {
        "title": "Eficiência na Logística",
        "start_date": (now - timedelta(days=10)).isoformat(),
        "end_date": (now + timedelta(days=80)).isoformat(),
        **overrides,
    }
    response = client.post(f"{API}/objectives", params={"workspace_id": workspace_id}, json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def create_kr(client, headers, objective_id, **overrides):
    payload = {
        "code": "8.1",
        "title": "Custo Logístico",
        "indicator_type": "decimal",
        "direction": "increase",
        "cadence": "weekly",
        "baseline_value": 0,
        "target_value": 100,
        **overrides,
    }
    response = client.post(f"{API}/objectives/{objective_id}/key-results", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def create_initiative(client, headers, kr_id, **overrides):
    payload = {"title": "Implantar Auditoria", "weight_percent": 100, **overrides}
    response = client.post(f"{API}/key-results/{kr_id}/initiatives", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def create_okr_task(client, headers, initiative_id, **overrides):
    payload = {"title": "Contar setor A", "weight_percent": 100, **overrides}
    response = client.post(f"{API}/initiatives/{initiative_id}/tasks", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def create_okr_action(client, headers, task_id, **overrides):
    payload = {"title": "Separar etiquetas", "weight_percent": 100, **overrides}
    response = client.post(f"{API}/tasks/{task_id}/actions", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_objective_detail_with_no_key_results_has_zero_performance(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    objective = create_objective(client, headers, workspace_id)

    response = client.get(f"{API}/objectives/{objective['id']}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["performance_percent"] == 0.0
    assert body["key_results"] == []


def test_key_result_progress_rolls_up_from_actions_through_initiatives(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    objective = create_objective(client, headers, workspace_id)
    kr = create_kr(client, headers, objective["id"])

    initiative = create_initiative(client, headers, kr["id"], weight_percent=100)
    task = create_okr_task(client, headers, initiative["id"], weight_percent=100)
    create_okr_action(client, headers, task["id"], title="A1", weight_percent=60, is_completed=True)
    create_okr_action(client, headers, task["id"], title="A2", weight_percent=40, is_completed=False)

    response = client.get(f"{API}/key-results/{kr['id']}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    # task progress = 60%*100 + 40%*0 = 60
    # initiative progress = 100%*60 / 100 = 60
    assert body["initiatives"][0]["progress_percent"] == 60.0
    assert body["initiatives"][0]["contribution_percent"] == 60.0
    assert body["initiatives_rollup_percent"] == 60.0
    # no checkins yet -> overall progress falls back to initiatives rollup
    assert body["progress_percent"] == 60.0


def test_checkin_comparatives_for_increase_direction_kr(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    objective = create_objective(client, headers, workspace_id)
    kr = create_kr(client, headers, objective["id"], baseline_value=0, target_value=100, direction="increase")

    now = datetime.now(timezone.utc)
    client.post(
        f"{API}/key-results/{kr['id']}/checkins",
        json={"period_start": (now - timedelta(days=14)).isoformat(), "period_end": (now - timedelta(days=7)).isoformat(), "value": 50},
        headers=headers,
    )
    client.post(
        f"{API}/key-results/{kr['id']}/checkins",
        json={"period_start": (now - timedelta(days=7)).isoformat(), "period_end": now.isoformat(), "value": 80},
        headers=headers,
    )

    response = client.get(f"{API}/key-results/{kr['id']}", headers=headers)
    body = response.json()
    assert body["current_value"] == 80
    assert body["previous_value"] == 50
    assert body["variation_abs"] == 30
    assert body["variation_pct"] == 60.0
    assert body["average_to_date"] == 65.0
    assert body["best_value"] == 80
    assert body["worst_value"] == 50
    assert body["progress_percent"] == 80.0
    assert body["gap_to_target"] == -20
    assert body["trend_direction"] == "up"
    assert body["trend_label"] == "positive"


def test_checkin_comparatives_for_decrease_direction_kr(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    objective = create_objective(
        client, headers, workspace_id,
        start_date=datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
        end_date=datetime(2026, 3, 1, tzinfo=timezone.utc).isoformat(),
    )
    kr = create_kr(client, headers, objective["id"], baseline_value=200, target_value=100, direction="decrease", cadence="weekly")

    client.post(
        f"{API}/key-results/{kr['id']}/checkins",
        json={
            "period_start": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
            "period_end": datetime(2026, 1, 8, tzinfo=timezone.utc).isoformat(),
            "value": 150,
        },
        headers=headers,
    )
    client.post(
        f"{API}/key-results/{kr['id']}/checkins",
        json={
            "period_start": datetime(2026, 1, 8, tzinfo=timezone.utc).isoformat(),
            "period_end": datetime(2026, 1, 15, tzinfo=timezone.utc).isoformat(),
            "value": 120,
        },
        headers=headers,
    )

    response = client.get(f"{API}/key-results/{kr['id']}", headers=headers)
    body = response.json()
    assert body["current_value"] == 120
    assert body["previous_value"] == 150
    assert body["variation_abs"] == -30
    assert body["variation_pct"] == -20.0
    assert body["average_to_date"] == 135.0
    assert body["best_value"] == 120
    assert body["worst_value"] == 150
    assert body["progress_percent"] == 80.0
    assert body["gap_to_target"] == 20
    assert body["trend_direction"] == "down"
    assert body["trend_label"] == "positive"

    remaining_days = (datetime(2026, 3, 1, tzinfo=timezone.utc) - datetime(2026, 1, 15, tzinfo=timezone.utc)).days
    periods_remaining = remaining_days / 7
    expected_forecast = round(-30 * (1 + periods_remaining) + 150, 2)
    assert body["forecast_value"] == expected_forecast
    assert body["forecast_hits_target"] is True


def test_objective_performance_averages_key_result_progress(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    objective = create_objective(client, headers, workspace_id)
    kr_a = create_kr(client, headers, objective["id"], code="A", baseline_value=0, target_value=100)
    kr_b = create_kr(client, headers, objective["id"], code="B", baseline_value=0, target_value=100)

    now = datetime.now(timezone.utc)
    client.post(
        f"{API}/key-results/{kr_a['id']}/checkins",
        json={"period_start": now.isoformat(), "period_end": now.isoformat(), "value": 100},
        headers=headers,
    )
    client.post(
        f"{API}/key-results/{kr_b['id']}/checkins",
        json={"period_start": now.isoformat(), "period_end": now.isoformat(), "value": 0},
        headers=headers,
    )

    response = client.get(f"{API}/objectives/{objective['id']}", headers=headers)
    assert response.json()["performance_percent"] == 50.0


def test_executive_summary_counts_and_completion(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    objective = create_objective(client, headers, workspace_id)
    kr = create_kr(client, headers, objective["id"])
    initiative = create_initiative(client, headers, kr["id"])
    task_done = create_okr_task(client, headers, initiative["id"], title="T1", is_completed=True)
    task_pending = create_okr_task(client, headers, initiative["id"], title="T2", is_completed=False)
    create_okr_action(client, headers, task_done["id"], title="A1", is_completed=True)

    response = client.get(f"{API}/workspaces/{workspace_id}/executive-summary", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["objectives_count"] == 1
    assert body["key_results_count"] == 1
    assert body["initiatives_count"] == 1
    assert body["tasks_count"] == 2
    assert body["actions_count"] == 1
    # leaf items = 2 tasks + 1 action = 3, completed = task_done + action = 2
    assert body["completed_percent"] == round(2 / 3 * 100, 1)


def test_alerts_flag_missing_owner_weight_mismatch_overdue_items_and_below_target(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    objective = create_objective(client, headers, workspace_id)
    kr = create_kr(client, headers, objective["id"], baseline_value=0, target_value=100, direction="increase")
    create_initiative(client, headers, kr["id"], weight_percent=40)

    now = datetime.now(timezone.utc)
    client.post(
        f"{API}/key-results/{kr['id']}/checkins",
        json={"period_start": (now - timedelta(days=7)).isoformat(), "period_end": now.isoformat(), "value": 10},
        headers=headers,
    )

    initiative2 = create_initiative(client, headers, kr["id"], title="Segunda", weight_percent=40)
    overdue_task = create_okr_task(
        client, headers, initiative2["id"], title="Atrasada",
        due_date=(now - timedelta(days=2)).isoformat(), is_completed=False,
    )
    client.post(
        f"{API}/tasks/{overdue_task['id']}/actions",
        json={"title": "Ação vencida", "due_date": (now - timedelta(days=1)).isoformat(), "is_completed": False},
        headers=headers,
    )

    response = client.get(f"{API}/workspaces/{workspace_id}/alerts", headers=headers)
    assert response.status_code == 200
    messages = [a["message"] for a in response.json()]
    assert "KR sem responsável definido." in messages
    assert any("Soma dos pesos das iniciativas" in m for m in messages)
    assert "KR abaixo da meta." in messages
    assert "Tarefa atrasada." in messages
    assert "Ação vencida." in messages


def test_okr_access_control_isolated_by_workspace(client):
    token_a = register_and_login(client, email="a@rbm.com")
    headers_a = auth_headers(token_a)
    workspace_a = get_default_workspace_id(client, headers_a)
    objective = create_objective(client, headers_a, workspace_a)
    kr = create_kr(client, headers_a, objective["id"])
    initiative = create_initiative(client, headers_a, kr["id"])
    task = create_okr_task(client, headers_a, initiative["id"])
    action = create_okr_action(client, headers_a, task["id"])

    token_b = register_and_login(client, email="b@rbm.com")
    headers_b = auth_headers(token_b)

    assert client.get(f"{API}/objectives/{objective['id']}", headers=headers_b).status_code == 404
    assert client.get(f"{API}/key-results/{kr['id']}", headers=headers_b).status_code == 404
    assert client.put(f"{API}/initiatives/{initiative['id']}", json={"title": "x"}, headers=headers_b).status_code == 404
    assert client.put(f"{API}/tasks/{task['id']}", json={"title": "x"}, headers=headers_b).status_code == 404
    assert client.put(f"{API}/actions/{action['id']}", json={"title": "x"}, headers=headers_b).status_code == 404


def test_checkin_rejects_end_before_start(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    objective = create_objective(client, headers, workspace_id)
    kr = create_kr(client, headers, objective["id"])

    now = datetime.now(timezone.utc)
    response = client.post(
        f"{API}/key-results/{kr['id']}/checkins",
        json={"period_start": now.isoformat(), "period_end": (now - timedelta(days=1)).isoformat(), "value": 10},
        headers=headers,
    )
    assert response.status_code == 400


def test_initiative_detail_includes_nested_tasks_and_actions(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    objective = create_objective(client, headers, workspace_id)
    kr = create_kr(client, headers, objective["id"])
    initiative = create_initiative(client, headers, kr["id"])
    task = create_okr_task(client, headers, initiative["id"], weight_percent=100)
    create_okr_action(client, headers, task["id"], title="A1", weight_percent=100, is_completed=True)

    response = client.get(f"{API}/initiatives/{initiative['id']}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["tasks"]) == 1
    assert body["tasks"][0]["progress_percent"] == 100.0
    assert len(body["tasks"][0]["actions"]) == 1
    assert body["progress_percent"] == 100.0


def test_delete_key_result_cascades_to_initiatives_tasks_actions(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    workspace_id = get_default_workspace_id(client, headers)
    objective = create_objective(client, headers, workspace_id)
    kr = create_kr(client, headers, objective["id"])
    initiative = create_initiative(client, headers, kr["id"])
    create_okr_task(client, headers, initiative["id"])

    response = client.delete(f"{API}/key-results/{kr['id']}", headers=headers)
    assert response.status_code == 204
    assert client.get(f"{API}/key-results/{kr['id']}", headers=headers).status_code == 404
