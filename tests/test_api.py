import pytest
import src.app_with_otel as app_module
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    app_module.storage.db_path = str(tmp_path / "test.db")
    with TestClient(app_module.app) as c:
        yield c
    app_module.storage.db_path = "data/metrics.db"


def test_summary_empty(client):
    r = client.get("/summary")
    assert r.status_code == 200
    data = r.json()
    assert "status_counts" in data
    assert "avg_duration_ms" in data
    assert "flaky_count" in data
    assert "recent_failures" in data


def test_post_metric(client):
    payload = {
        "agent_id": "agent-1",
        "build_id": "b-1",
        "status": "PASS",
        "duration_ms": 1234,
    }
    r = client.post("/metrics", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "received"
    assert r.json()["is_flaky"] is False

    r2 = client.get("/summary")
    assert r2.status_code == 200
    data = r2.json()
    assert data["status_counts"].get("PASS") == 1
    assert data["avg_duration_ms"] == 1234


def test_post_metric_invalid(client):
    r = client.post("/metrics", json={"bad": "data"})
    assert r.status_code == 422
