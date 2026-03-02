import pytest
import src.app_with_otel as app_module
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    app_module.storage.db_path = str(tmp_path / "test.db")
    with TestClient(app_module.app) as c:
        yield c
    app_module.storage.db_path = "data/metrics.db"


def test_post_and_get_summary(client):
    payload = {
        "agent_id": "agent-1",
        "build_id": "b-int-1",
        "status": "PASS",
        "duration_ms": 5000,
    }
    r = client.post("/metrics", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "received"
    assert body["is_flaky"] is False

    r2 = client.get("/summary")
    assert r2.status_code == 200
    data = r2.json()
    assert data["status_counts"].get("PASS") == 1
    assert data["avg_duration_ms"] == 5000
    assert data["flaky_count"] == 0


def test_flaky_detection_end_to_end(client):
    # First run: PASS — not flaky yet
    r1 = client.post("/metrics", json={
        "agent_id": "agent-1",
        "build_id": "b-flaky",
        "status": "PASS",
        "duration_ms": 1000,
    })
    assert r1.json()["is_flaky"] is False

    # Second run: FAIL — now flaky
    r2 = client.post("/metrics", json={
        "agent_id": "agent-2",
        "build_id": "b-flaky",
        "status": "FAIL",
        "duration_ms": 2000,
    })
    assert r2.json()["is_flaky"] is True

    summary = client.get("/summary").json()
    assert summary["flaky_count"] == 1
    assert "b-flaky" in summary["flaky_builds"]


def test_multiple_agents(client):
    for i in range(3):
        client.post("/metrics", json={
            "agent_id": f"agent-{i}",
            "build_id": f"b-multi-{i}",
            "status": "PASS",
            "duration_ms": (i + 1) * 1000,
        })

    summary = client.get("/summary").json()
    assert summary["status_counts"].get("PASS") == 3
    assert summary["avg_duration_ms"] == 2000  # (1000+2000+3000)/3


def test_fail_shows_in_recent_failures(client):
    client.post("/metrics", json={
        "agent_id": "agent-1",
        "build_id": "b-fail",
        "status": "FAIL",
        "duration_ms": 9000,
    })

    summary = client.get("/summary").json()
    assert any(f["build_id"] == "b-fail" for f in summary["recent_failures"])
