from pathlib import Path

import pytest

FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


# Unmatched paths go to the frontend routes, which need the build
needs_frontend = pytest.mark.skipif(
    not FRONTEND_DIST.exists(), reason="frontend not built (npm run build)"
)


@needs_frontend
def test_root_serves_frontend(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


@needs_frontend
def test_unknown_api_path_is_json_404(client):
    response = client.get("/stats/unknown")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_db(client):
    response = client.get("/health/db")
    assert response.status_code == 200
