# ADR-003: Storage Strategy

**Status:** Accepted
**Date:** 2026-04-11
**Decision Makers:** Gabriel Mendoza

## Context

The SMT handles four categories of data with different access patterns, consistency requirements, and lifecycle characteristics:

1. **Time-series metrics:** High write throughput, time-ordered, aggregation-heavy reads.
2. **Transactional data:** Infractions, vehicle records, fines. Requires ACID guarantees.
3. **Binary objects:** Infraction photos (images from cameras/simulation).
4. **Hot/cached data:** Recently computed aggregations for dashboard reads.

The DB-per-service principle requires logical separation of data ownership.

## Decision

Four storage technologies, each optimized for its workload:

| Storage | Technology | Data | Owner Service |
|---|---|---|---|
| Time-series | TimescaleDB (on PostgreSQL 16) | Traffic metrics, speed stats, aggregations | Metrics & Analytics Service |
| Transactional | PostgreSQL 16 | Infractions, vehicle events, notification logs | Vehicles & Infractions, Notifications |
| Object | MinIO (S3-compatible) | Infraction photos | Stream Processor (write), Vehicles Service (read) |
| Cache | Redis 7.x | Aggregated metrics (TTL-based) | Metrics & Analytics Service |

### DB-per-service enforcement

- **Physical deployment:** Shared PostgreSQL cluster (capstone pragmatism).
- **Logical separation:** Per-service schemas (`metrics_schema`, `infractions_schema`, `notifications_schema`).
- **Rules:** No cross-schema JOINs. No shared sequences. No foreign keys crossing service boundaries. Cross-service data access goes through service APIs only.

### Alternatives Considered

| Data Type | Alternative | Why Rejected |
|---|---|---|
| Time-series | InfluxDB | Different query language (Flux), separate driver, more infra to operate. TimescaleDB leverages existing PostgreSQL knowledge. |
| Transactional | MongoDB | No ACID guarantees for infraction records. Relational integrity matters when issuing financial fines. |
| Object | AWS S3 directly | Requires cloud account and cost management. MinIO is self-hosted, S3-compatible, and swappable to S3 with config change only. |
| Cache | Memcached | Redis provides richer data structures (sorted sets for leaderboards, pub/sub for notifications). |

## Consequences

**Positive:**
- TimescaleDB and PostgreSQL share the same ecosystem (driver, query language, operational knowledge).
- MinIO's S3 compatibility means zero code changes when migrating to cloud object storage.
- Redis provides sub-millisecond reads for dashboard responsiveness.

**Negative:**
- TimescaleDB continuous aggregates add write amplification at high ingest rates (production scale concern, not capstone scale).
- Shared physical cluster means no true resource isolation between services (acceptable for capstone).

**Portability mitigations:**
- Repository abstraction layer isolates all TimescaleDB-specific queries behind a generic interface.
- All MinIO path segments are environment-configurable.
- Redis can be replaced by Valkey (open-source fork) as a drop-in alternative.
