# Project README

# Real-time Build Telemetry Dashboard with OpenTelemetry

A comprehensive CI/CD telemetry system for tracking build metrics, detecting flaky tests, and monitoring pipeline health in real-time.

## Features

- 📊 Real-time build metrics visualization
- 🔍 Flaky test detection with statistical analysis
- 📈 Distributed tracing with OpenTelemetry
- 🚨 Prometheus alerts for build failures
- 📱 WebSocket-based live updates
- 🎯 Multi-agent support for distributed builds

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/vallurun/realtime-build-telemetry-dashboard.git
cd realtime-build-telemetry-dashboard

# Start all services
docker-compose up -d

# Access dashboards
# - Telemetry Dashboard: http://localhost:8000
# - Grafana: http://localhost:3000 (admin/admin)
# - Jaeger UI: http://localhost:16686
# - Prometheus: http://localhost:9090