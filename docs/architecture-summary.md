# Architecture Summary & 12-Factor Compliance

The SMT is a Cloud-Native system built for reliability and scale.

## Core Design Principles

1.  **Event-Driven (EDA):** Uses Apache Kafka as a persistent shock absorber for telemetry bursts.
2.  **Stateless Processes:** No service stores state on its local disk. All state is in-memory (simulation) or on the broker.
3.  **Dependency Isolation:** Each microservice is containerized with its specific runtime requirements.

## 12-Factor Adherence

| Factor | Implementation in SMT |
| :--- | :--- |
| **I. Codebase** | Monorepo structure with independent service logic. |
| **II. Dependencies** | Isolated `requirements.txt` per service. |
| **III. Config** | Environment variables via `shared/settings.py`. |
| **IV. Backing Services** | Kafka and APIs treated as attached resources. |
| **V. Build, Release, Run** | Strict separation through Docker CI/CD pipelines. |
| **VI. Processes** | Stateless FastAPI and Streamlit processes. |
| **VII. Port Binding** | Each service self-hosts and exports its own port. |
| **VIII. Concurrency** | Horizontally scalable via Kafka partitions. |
| **IX. Disposability** | Fast startup and graceful SIGTERM handling. |
| **X. Dev/Prod Parity** | Azure VM runs the exact same images as local dev. |
| **XI. Logs** | Structured JSON logs to stdout. |
| **XII. Admin Processes** | Health and seed tasks integrated into the life-cycle. |

## Observability Stack

- **Metrics:** `/metrics` endpoint in Prometheus format (Latency, Traffic, Errors, Saturation).
- **Health:** `/health` endpoint with deep dependency checking.
- **Traceability:** Correlation IDs across JSON logs.
