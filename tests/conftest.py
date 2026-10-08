import os

# Tests must not depend on a developer's .env; real env vars still take precedence.
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")

import pytest  # noqa: E402

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


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
