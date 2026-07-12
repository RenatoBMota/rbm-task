from tests.conftest import register_and_login, auth_headers


def test_register_creates_admin_for_first_user(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "first@rbm.com", "full_name": "First User", "password": "senha123"},
    )
    assert response.status_code == 201
    assert response.json()["role"] == "admin"


def test_second_registration_is_member(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "first@rbm.com", "full_name": "First", "password": "senha123"},
    )
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "second@rbm.com", "full_name": "Second", "password": "senha123"},
    )
    assert response.json()["role"] == "member"


def test_duplicate_email_rejected(client):
    payload = {"email": "dup@rbm.com", "full_name": "Dup", "password": "senha123"}
    client.post("/api/v1/auth/register", json=payload)
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400


def test_login_wrong_password_rejected(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "user@rbm.com", "full_name": "User", "password": "senha123"},
    )
    response = client.post("/api/v1/auth/login", json={"email": "user@rbm.com", "password": "wrong"})
    assert response.status_code == 401


def test_login_returns_tokens(client):
    token = register_and_login(client)
    assert token


def test_refresh_token_issues_new_access_token(client):
    register_and_login(client)
    login = client.post("/api/v1/auth/login", json={"email": "admin@rbm.com", "password": "senha123"})
    refresh_token = login.json()["refresh_token"]
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_protected_endpoint_requires_token(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code in (401, 403)


def test_protected_endpoint_works_with_token(client):
    token = register_and_login(client)
    response = client.get("/api/v1/users/me", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["email"] == "admin@rbm.com"
