# ADR-002: Microservices Architecture Style

**Status:** Accepted
**Date:** 2026-04-09
**Decision Makers:** Gabriel Mendoza

## Context

Three architectural styles were evaluated for the SMT:

1. **Monolith Modular:** Single deployable unit with internal module boundaries.
2. **SOA (Service-Oriented Architecture):** Coarse-grained services with centralized bus coordination.
3. **Microservices:** Fine-grained, independently deployable services with decentralized communication.

The system processes ~4M events/day with Poisson-distributed arrival rates, serves dashboard queries, and handles infraction alerting — each with fundamentally different scaling and latency requirements.

## Decision

**Microservices architecture**, with the following pragmatic constraint for the capstone: all services live in a **single monorepo** for development convenience. In production, each service would have its own repository and deployment pipeline.

### Justification

1. **Different scaling profiles:** IoT Gateway handles ~46 events/second sustained (3-4x peaks). Metrics Service handles dozens of queries/second. Orders-of-magnitude difference demands independent scaling.
2. **Different SLAs:** Ingestion is durability-critical (no event loss). Dashboard queries are latency-optimized. Notifications are eventual. Different services, different configurations.
3. **Clear domain boundaries:** Metrics, Vehicles/Infractions, Notifications, Ingestion, Processing — each has well-defined responsibility and low inter-service coupling.
4. **Independent deployment:** A service can be rewritten, redeployed, or scaled without touching any other.

### Alternatives Rejected

- **Monolith Modular:** Sufficient for capstone demo scale, but cannot demonstrate independent scaling of the ingestion path vs query path. Also doesn't align with the cloud-native principles the rubric evaluates.
- **SOA:** The centralized bus adds coordination overhead without solving a problem that Kafka's topic-based routing doesn't already handle more naturally. Risk of accumulating responsibilities into monolith-distributed pattern.

## Consequences

**Positive:**
- Each service scales independently based on its actual load.
- Failure isolation — one service failing doesn't bring down the system.
- Technology flexibility — services can use different languages/frameworks if needed.

**Negative:**
- Operational complexity: distributed tracing, service discovery, contract management.
- Network latency between services (mitigated by co-locating in the same cluster).
- For a solo developer, maintaining multiple service boundaries adds development overhead.

**Capstone Pragmatism:**
- Monorepo structure simulates microservices boundaries within a single repository.
- Docker Compose orchestrates all services locally.
- The architecture is designed for Kubernetes but the capstone demo runs on Docker Compose.
