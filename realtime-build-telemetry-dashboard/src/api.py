from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from typing import List
import statistics

app = FastAPI(title="Realtime Build Telemetry Dashboard")

class Metric(BaseModel):
    build_id: str
    status: str
    duration_sec: float

metrics_store: List[Metric] = []
websockets: List[WebSocket] = []

@app.post("/metrics")
async def add_metric(metric: Metric):
    metrics_store.append(metric)
    # broadcast to all connected clients
    for ws in websockets:
        await ws.send_json(metric.dict())
    return {"ok": True}

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    websockets.append(ws)
    try:
        while True:
            await ws.receive_text()
    except Exception:
        pass
    finally:
        websockets.remove(ws)

@app.get("/summary")
async def summary():
    if not metrics_store:
        return {"total": 0, "success_rate": 0, "avg_duration": 0}
    total = len(metrics_store)
    successes = sum(1 for m in metrics_store if m.status == "success")
    avg_duration = statistics.mean(m.duration_sec for m in metrics_store)
    return {"total": total, "success_rate": successes / total, "avg_duration": avg_duration}
