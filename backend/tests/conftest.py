import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import app.models  # noqa: F401 — registers all models on Base.metadata
from app.core.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def register_and_login(client: TestClient, email: str = "admin@rbm.com", password: str = "senha123") -> str:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Test User", "password": password},
    )
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def get_default_workspace_id(client: TestClient, headers: dict) -> int:
    workspaces = client.get("/api/v1/workspaces", headers=headers).json()
    return workspaces[0]["id"]


def create_project(client: TestClient, headers: dict, workspace_id: int, name: str = "P", **overrides) -> dict:
    # Wide default window so incidental "yesterday"/"next week" task dates used
    # across tests comfortably fall inside the project's required date range.
    now = datetime.now(timezone.utc)
    payload = {
        "name": name,
        "workspace_id": workspace_id,
        "start_date": (now - timedelta(days=60)).isoformat(),
        "end_date": (now + timedelta(days=180)).isoformat(),
        **overrides,
    }
    return client.post("/api/v1/projects", json=payload, headers=headers).json()
