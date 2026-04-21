# ADR-001: Hybrid Event-Driven Architecture

**Status:** Accepted
**Date:** 2026-04-09
**Decision Makers:** Gabriel Mendoza

## Context

The SMT must handle ~4M vehicle detection events per day from 200 distributed locations while simultaneously serving dashboard queries and infraction lookups. The event arrival rate follows a Poisson distribution, meaning traffic is bursty and non-uniform. The system also needs to support near-real-time alerting for speed infractions and weather conditions.

Two communication paradigms were evaluated:
- **Pure synchronous (request/response):** All processing happens inline when an event arrives.
- **Pure asynchronous (event-driven):** All communication goes through a message broker.
- **Hybrid:** Ingestion is event-driven; user-facing queries are synchronous REST.

## Decision

The SMT uses a **hybrid communication model:**
- **Ingestion pipeline:** Fully asynchronous via Apache Kafka. Sensors publish events to the IoT Gateway, which forwards them to Kafka. The Stream Processor consumes events asynchronously.
- **Query pipeline:** Synchronous REST via the API Gateway. Dashboard and authority queries follow standard request/response semantics.
- **Alert delivery:** Asynchronous. The Notifications Service consumes alert events from Kafka independently.

## Consequences

**Positive:**
- Kafka absorbs Poisson variance in arrival rates — peak-hour bursts don't overwhelm downstream processors.
- Ingestion and query pipelines are decoupled — scaling one doesn't affect the other.
- Alert delivery is independent of ingestion speed.

**Negative:**
- Operational complexity of running Kafka (even in KRaft mode).
- Eventual consistency between event ingestion and query availability (acceptable per requirements).
- Debugging async flows requires distributed tracing (correlation IDs, OpenTelemetry).

**Risks:**
- Kafka consumer lag during sustained peaks could delay infraction detection. Mitigated by horizontal scaling of Stream Processor instances.
