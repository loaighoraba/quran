from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


# Unmatched paths go to the frontend routes, which need the build
needs_frontend = pytest.mark.skipif(
    not FRONTEND_DIST.exists(), reason="frontend not built (npm run build)"
)


@needs_frontend
def test_root_serves_frontend():
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


@needs_frontend
def test_unknown_api_path_is_json_404():
    response = client.get("/stats/unknown")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
