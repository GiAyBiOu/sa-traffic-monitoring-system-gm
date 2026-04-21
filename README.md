# TMS — Traffic Monitoring System (Bolivia)

National Traffic Monitoring System simulation — cloud-native microservices architecture monitoring 8 locations across Santa Cruz, La Paz, and Cochabamba.

## Architecture

```
Simulator ──► IoT Gateway ──► Kafka ──► Stream Processor ──► Metrics/Infractions
                                                                     │
                                                               Dashboard (Streamlit)
```

| Service | Port | Role |
|---------|------|------|
| IoT Gateway | 8001 | Event ingestion, validation, Kafka publishing |
| Stream Processor | 8002 | Kafka consumer, infraction detection, metric aggregation |
| Metrics Service | 8003 | Read-optimized API for traffic analytics |
| Vehicles Service | 8004 | Infraction records and vehicle trajectory |
| Dashboard | 8501 | Real-time Streamlit visualization with CDN video feeds |
| Simulator | — | Mock event generator (Poisson/Gaussian/Markov) |
| Kafka | 9092 | Event bus (KRaft mode) |

## Monitored Locations (Bolivia)

| ID | Location | City | Speed Limit |
|---|---|---|---|
| loc-scz-001 | Av. Cristo Redentor | Santa Cruz | 60 km/h |
| loc-scz-002 | Doble Via La Guardia | Santa Cruz | 80 km/h |
| loc-scz-003 | Segundo Anillo - Av. Santos Dumont | Santa Cruz | 50 km/h |
| loc-scz-004 | Av. Banzer - 4to Anillo | Santa Cruz | 60 km/h |
| loc-lpz-001 | Autopista La Paz - El Alto | La Paz | 80 km/h |
| loc-lpz-002 | Av. 6 de Agosto - Sopocachi | La Paz | 40 km/h |
| loc-cbba-001 | Av. Blanco Galindo | Cochabamba | 70 km/h |
| loc-cbba-002 | Av. Heroinas - Centro | Cochabamba | 40 km/h |

## Quick Start

### Docker Compose (Recommended)

```powershell
cp .env.example .env
docker compose up --build -d
docker compose ps
```

Dashboard: `http://localhost:8501`

### Local Development (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dashboard.txt -r requirements-simulator.txt
cp .env.example .env

# Start services in separate terminals
uvicorn services.iot_gateway.main:app --port 8001 --reload
uvicorn services.stream_processor.main:app --port 8002 --reload
uvicorn services.metrics_service.main:app --port 8003 --reload
uvicorn services.vehicles_service.main:app --port 8004 --reload
streamlit run services/dashboard/app.py --server.port 8501
python -m services.simulator.main
```

### Run Load Test

```powershell
python scripts/load_test.py
```

## API Reference

Every service exposes `/health` and `/metrics` (Prometheus format).

- **Gateway** `:8001` — `POST /api/v1/events/vehicle`, `POST /api/v1/events/batch`, `GET /api/v1/config/locations`, `GET /api/v1/config/video-feeds`
- **Processor** `:8002` — `POST /api/v1/process`, `POST /api/v1/metrics/flush`, `GET /api/v1/infractions`, `GET /api/v1/metrics`
- **Metrics** `:8003` — `GET /api/v1/metrics?city=Santa Cruz`, `GET /api/v1/metrics/{location_id}`, `GET /api/v1/metrics/summary`, `GET /api/v1/locations`
- **Vehicles** `:8004` — `GET /api/v1/infractions`, `GET /api/v1/infractions/{id}`, `GET /api/v1/vehicles/{plate}/trajectory`

## 12-Factor Compliance

| Factor | Implementation |
|--------|---------------|
| I. Codebase | Git monorepo |
| II. Dependencies | Pinned `requirements.txt` |
| III. Config | Environment variables via `.env` |
| IV. Backing Services | Kafka as attached resource |
| V. Build/Release/Run | Dockerfile per service |
| VI. Processes | Stateless FastAPI services |
| VII. Port Binding | Self-contained with explicit ports |
| VIII. Concurrency | `docker compose up --scale` |
| IX. Disposability | Fast startup, graceful shutdown |
| X. Dev/Prod Parity | Same Docker images everywhere |
| XI. Logs | JSON structured logs to stdout |
| XII. Admin | `/health`, `/metrics`, load test scripts |

## Observability (M6)

- **Structured Logging**: JSON to stdout with service name, timestamp, level, trace context
- **Prometheus Metrics**: Every service exposes `/metrics` — request count, latency, errors, uptime
- **Health Checks**: `/health` per service with dependency status
- **Load Testing**: `scripts/load_test.py` with concurrent workers, throughput/latency reporting

## CI/CD (M7)

GitHub Actions pipeline in `.github/workflows/ci.yml`:
1. **Lint & Test** — Import verification, smoke tests with generated data
2. **Build Containers** — `docker compose build` all images
3. **Health Check** — Start stack, verify all `/health` endpoints
4. **Metrics Verification** — Confirm Prometheus endpoints respond

## Mathematical Models

- **Poisson** — Vehicle arrival count per interval (`λ` per location)
- **Gaussian** — Individual vehicle speed distribution (`μ`, `σ` per road type)
- **Markov Chain** — Traffic state transitions (free_flow ↔ congestion ↔ incident)
- **Weibull-ready** — Speed modeling under variable conditions

## Azure Deployment

### VM Recommendation (Budget: $100 for 4 days)

**VM Size: `Standard_B2ms`** — 2 vCPUs, 8 GB RAM, $0.0832/hr ≈ **$8/day = $32 for 4 days**

```bash
# 1. Create resource group
az group create --name rg-tms-bolivia --location eastus

# 2. Create VM
az vm create \
  --resource-group rg-tms-bolivia \
  --name vm-tms \
  --image Ubuntu2404 \
  --size Standard_B2ms \
  --admin-username tmsadmin \
  --generate-ssh-keys \
  --public-ip-sku Standard \
  --nsg-rule SSH

# 3. Open ports
az vm open-port --resource-group rg-tms-bolivia --name vm-tms --port 8001,8002,8003,8004,8501,9092 --priority 1001

# 4. SSH and deploy
ssh tmsadmin@<PUBLIC_IP>
sudo apt update && sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
# logout/login
git clone <your-repo-url>
cd sa-traffic-monitoring-system-gm
cp .env.example .env
docker compose up --build -d

# 5. Verify
docker compose ps
curl http://localhost:8001/health

# 6. CLEANUP after 4 days
az group delete --name rg-tms-bolivia --yes
```

Dashboard accessible at: `http://<PUBLIC_IP>:8501`

## Tech Stack

Python 3.12 · FastAPI · Streamlit · Apache Kafka (KRaft) · Plotly · NumPy · SciPy · Docker Compose

## Project Structure

```
sa-traffic-monitoring-system-gm/
├── shared/                    # Domain code
│   ├── settings.py            # Env config (12-Factor III)
│   ├── logger.py              # Structured JSON logging
│   ├── models.py              # VehicleEvent, TrafficMetric, Infraction
│   ├── generators.py          # Poisson/Gaussian/Markov generators
│   ├── locations.py           # Bolivia monitoring locations
│   └── observability.py       # Prometheus metrics middleware
├── services/
│   ├── iot_gateway/           # Event ingestion
│   ├── stream_processor/      # Event processing
│   ├── metrics_service/       # Analytics API
│   ├── vehicles_service/      # Infractions
│   ├── dashboard/             # Streamlit UI
│   └── simulator/             # Mock event generator
├── scripts/
│   └── load_test.py           # Concurrent load testing
├── .github/workflows/ci.yml   # CI/CD pipeline
├── docs/adr/                  # Architecture Decision Records
├── Dockerfile.*               # Per-service containers
├── docker-compose.yml         # Orchestration
└── .env.example               # Config template
```
