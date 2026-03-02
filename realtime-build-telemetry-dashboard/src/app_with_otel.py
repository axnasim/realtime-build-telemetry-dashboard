import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import List

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from src.models import BuildMetric
from src.storage import MetricsStorage

# Configure OpenTelemetry
resource = Resource.create({
    "service.name": "build-telemetry-dashboard",
    "service.version": "1.0.0",
    "deployment.environment": os.getenv("ENVIRONMENT", "development"),
})

# Only enable OTLP export when an endpoint is explicitly configured
_otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

# Tracing setup
trace_provider = TracerProvider(resource=resource)
if _otel_endpoint:
    trace_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=_otel_endpoint + "/v1/traces"))
    )
trace.set_tracer_provider(trace_provider)

# Metrics setup
_metric_readers = []
if _otel_endpoint:
    _metric_readers.append(
        PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=_otel_endpoint + "/v1/metrics")
        )
    )
meter_provider = MeterProvider(resource=resource, metric_readers=_metric_readers)
metrics.set_meter_provider(meter_provider)

# Get tracer and meter
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Custom metrics
build_duration_histogram = meter.create_histogram(
    "build.duration",
    description="Build duration in milliseconds",
    unit="ms"
)

build_counter = meter.create_counter(
    "build.count",
    description="Total number of builds"
)

flaky_test_counter = meter.create_counter(
    "build.flaky_tests",
    description="Number of flaky test occurrences"
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()
storage = MetricsStorage()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await storage.init_db()
    yield
    # Cleanup if needed

app = FastAPI(lifespan=lifespan, title="Build Telemetry Dashboard with OpenTelemetry")

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

@app.post("/metrics")
async def post_metric(metric: BuildMetric):
    """Receive build metrics from CI/CD agents"""
    with tracer.start_as_current_span("receive_build_metric") as span:
        # Add span attributes
        span.set_attribute("build.id", metric.build_id)
        span.set_attribute("build.agent_id", metric.agent_id)
        span.set_attribute("build.status", metric.status)
        span.set_attribute("build.duration_ms", metric.duration_ms)
        
        # Record metrics
        build_counter.add(1, {
            "status": metric.status,
            "agent_id": metric.agent_id
        })
        
        build_duration_histogram.record(metric.duration_ms, {
            "status": metric.status,
            "agent_id": metric.agent_id
        })
        
        # Store in database
        await storage.insert_metric(metric)
        
        # Broadcast to WebSocket clients
        await manager.broadcast({
            "type": "new_metric",
            "data": metric.model_dump(mode="json")
        })
        
        # Check for flaky tests (if same build_id has multiple statuses)
        is_flaky = await storage.check_flaky_build(metric.build_id)
        if is_flaky:
            span.set_attribute("build.is_flaky", True)
            flaky_test_counter.add(1, {"build_id": metric.build_id})
            
            await manager.broadcast({
                "type": "flaky_test_detected",
                "data": {
                    "build_id": metric.build_id,
                    "agent_id": metric.agent_id
                }
            })
        
        return {"status": "received", "is_flaky": is_flaky}

@app.get("/summary")
async def get_summary():
    """Get aggregated build statistics"""
    with tracer.start_as_current_span("get_build_summary"):
        summary = await storage.get_summary()
        return summary

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the real-time dashboard"""
    with open("src/static/index.html", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)