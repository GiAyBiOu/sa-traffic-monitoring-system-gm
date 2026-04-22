# TMS — Traffic Monitoring System (Bolivia)

National Traffic Monitoring System simulation — cloud-native microservices architecture monitoring 8 locations across Santa Cruz, La Paz, and Cochabamba.

[![CI Pipeline](https://github.com/GiAyBiOu/sa-traffic-monitoring-system-gm/actions/workflows/ci.yml/badge.svg)](https://github.com/GiAyBiOu/sa-traffic-monitoring-system-gm/actions)

## Quick Start (Production/Demo)

To lift the entire stack (Gateway, Kafka, Processor, APIs, Dashboard, and Simulator):

```powershell
# 1. Clone the repository
git clone git@github.com:GiAyBiOu/sa-traffic-monitoring-system-gm.git
cd sa-traffic-monitoring-system-gm

# 2. Setup environment
cp .env.example .env

# 3. Build and Run
docker compose up --build -d

# 4. Access Dashboard
# http://localhost:8501
```

## 📖 Documentation

- [Architecture Summary & 12-Factor](./docs/architecture-summary.md)
- [C4 Model (Containers)](./docs/c4-model.md)
- [Mathematical Models & Simulation](./docs/mathematical-models.md)
- [Use Case Analysis](./docs/use-cases.md)
- [Architecture Decision Records (ADR)](./docs/adr/)

## 🛠 Tech Stack

- **Backend:** Python 3.12, FastAPI, Pydantic
- **Backbone:** Apache Kafka (KRaft mode)
- **UI:** Streamlit, Plotly
- **Infrastructure:** Docker Compose, Azure VM (Ubuntu)
- **Computer Vision:** YOLO (ultralytics)

## 📍 Monitored Locations

| City | Key Locations | Speed Limit |
|---|---|---|
| **Santa Cruz** | Cristo Redentor, Doble Via, 2do Anillo, Banzer | 50 - 80 km/h |
| **La Paz** | Autopista, Sopocachi | 40 - 80 km/h |
| **Cochabamba** | Blanco Galindo, Heroinas | 40 - 70 km/h |

## ⚙️ API Endpoints

Every service exposes `/health` and `/metrics` (Prometheus).
- **Gateway** (`:8001`) - Telemetry Ingestion
- **Processor** (`:8002`) - Real-time Enrichment
- **Metrics** (`:8003`) - Analytics API
- **Vehicles** (`:8004`) - Infraction History
- **Dashboard** (`:8501`) - Visual NOC

---
Developed as part of the **Jala University Capstone Project**.
Repository: [git@github.com:GiAyBiOu/sa-traffic-monitoring-system-gm.git](git@github.com:GiAyBiOu/sa-traffic-monitoring-system-gm.git)
