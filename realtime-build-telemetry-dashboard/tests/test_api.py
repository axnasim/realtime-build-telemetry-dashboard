from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)

def test_summary_empty():
    r = client.get('/summary')
    assert r.status_code == 200
    data = r.json()
    assert data['total'] >= 0

def test_post_metric():
    payload = {
        "agent_id": "agent-1",
        "build_id": "b-1",
        "status": "PASS",
        "duration_ms": 1234
    }
    r = client.post('/metrics', json=payload)
    assert r.status_code == 200
    r2 = client.get('/summary')
    assert r2.status_code == 200
    assert r2.json()['total'] >= 1
