"""Test fixtures.

Tests run against in-memory SQLite by default. Set TEST_DATABASE_URL to run the same
suite against PostgreSQL (CI does both), e.g.
    TEST_DATABASE_URL=postgresql+psycopg://jobboard:jobboard@localhost:5432/jobboard_test
"""

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db, make_engine
from app.main import create_app
from app.models import User
from app.schemas.user import UserCreate
from app.services import users as user_service

PASSWORD = "s3cret-pass"


def _make_test_engine() -> Engine:
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        return make_engine(url)
    engine = make_engine("sqlite://")
    engine.pool = StaticPool(engine.pool._creator)  # one shared in-memory DB

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _record):  # enforce FK cascades like PostgreSQL
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


@pytest.fixture(scope="session")
def engine() -> Engine:
    return _make_test_engine()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c


@pytest.fixture
def make_user(db: Session):
    def _make(username: str = "alice", *, superuser: bool = False) -> User:
        return user_service.create_user(
            db,
            UserCreate(username=username, email=f"{username}@example.com", password=PASSWORD),
            is_superuser=superuser,
        )

    return _make


def token_for(client: TestClient, username: str, password: str = PASSWORD) -> dict[str, str]:
    res = client.post("/api/v1/auth/token", data={"username": username, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


JOB = {
    "title": "Backend Engineer",
    "company": "Kaveri Labs",
    "company_url": "https://kaveri.example.com",
    "location": "Chennai",
    "description": "Build FastAPI services on PostgreSQL.",
}
