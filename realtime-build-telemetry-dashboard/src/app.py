from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from typing import Set
from .models import BuildEvent, Summary
from .storage import Store

app = FastAPI(title="Realtime Build Telemetry Dashboard")
app.mount("/", StaticFiles(directory="src/static", html=True), name="static")

store = Store()  # use ':memory:'; swap to a file path if you want persistence
clients: Set[WebSocket] = set()

async def broadcast_summary():
    summary = store.summary()
    payload = {"type": "summary", "data": summary}
    for ws in list(clients):
        try:
            await ws.send_json(payload)
        except Exception:
            try:
                await ws.close()
            finally:
                clients.discard(ws)

@app.post("/metrics")
async def add_metric(event: BuildEvent):
    store.insert_event(event.agent_id, event.build_id, event.status, event.duration_ms, event.timestamp)
    await broadcast_summary()
    return {"ok": True}

@app.get("/summary")
async def get_summary():
    return store.summary()

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    # send immediate summary on connect
    await broadcast_summary()
    try:
        while True:
            # We don't expect messages from client, but keep alive
            await ws.receive_text()
    except WebSocketDisconnect:
        clients.discard(ws)
