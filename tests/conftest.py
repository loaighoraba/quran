import os

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import SessionDep
from app.main import create_app

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


@pytest.fixture(scope="session")
def settings():
    settings = Settings(_env_file=".env.test")  # type: ignore[call-arg]
    assert settings.postgres_db.endswith("_test")  # make sure we are using a test database
    return settings


@pytest.fixture(scope="session")
def app(settings):
    return create_app(settings)


@pytest.fixture
def db_session(app):
    conn = app.state.engine.connect()
    trans = conn.begin()
    session = app.state.session_factory(bind=conn, join_transaction_mode="create_savepoint")
    yield conn
    session.close()
    trans.rollback()
    conn.close()


@pytest.fixture
def client(app, db_session):
    app.dependency_overrides[SessionDep] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def quran_db() -> None:
    """Load the full Quran into the test database; it must already be migrated.

    Opt-in with QURAN_TEST_DB=1, since loading replaces all data in the database.
    """
    if os.environ.get("QURAN_TEST_DB") != "1":
        pytest.skip("run with: uv run --env-file .env.test pytest (see README, Tests)")
    from app.config import get_settings
    from app.scripts import load_quran

    host = get_settings().postgres_host
    if host not in LOCAL_HOSTS:
        pytest.fail(f"Refusing to load test data into {host}; use a local database")
    load_quran.main()
