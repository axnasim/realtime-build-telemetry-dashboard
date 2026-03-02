# Realtime Build Telemetry Dashboard

A lightweight **real-time dashboard** for **distributed build/test telemetry**. Engineers can POST build events,
and a WebSocket channel streams updates to the dashboard in real time. Designed to be extended with **Azure Event Hubs**
and **Application Insights**.

## Highlights
- **FastAPI** backend with REST + WebSocket
- **Real-time UI** (Chart.js) showing pass/fail counts and average duration
- **SQLite** storage for simple analytics (can swap for Azure Data Explorer)
- **CI-ready** with pytest + GitHub Actions

## Run (local)
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.app:app --reload --port 8000
```

Open the dashboard at: http://localhost:8000

## Send events
```bash
curl -X POST http://localhost:8000/metrics -H "Content-Type: application/json" -d '{
  "agent_id": "agent-1",
  "build_id": "build-123",
  "status": "PASS",
  "duration_ms": 17432
}'
```

## Project Structure
```
realtime-build-telemetry-dashboard/
├─ src/
│  ├─ app.py         # FastAPI app + WebSocket broadcaster
│  ├─ models.py      # Pydantic models
│  ├─ storage.py     # SQLite storage & summary queries
│  └─ static/
│     └─ index.html  # Real-time dashboard (Chart.js)
├─ tests/
│  └─ test_api.py
├─ .github/workflows/
│  └─ ci.yml
├─ data/
│  └─ sample_events.jsonl
├─ requirements.txt
└─ README.md
```

## Azure Integration (next steps)
- Replace SQLite with **Azure Data Explorer (ADX)** to store events and run KQL queries.
- Push logs/metrics to **Application Insights**.
- Ingest events from **Azure Event Hubs** and fan out to WebSocket clients.

## License
MIT
