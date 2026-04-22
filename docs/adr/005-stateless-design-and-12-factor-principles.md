# ADR-005: Stateless Service Design and 12-Factor Principles

**Status:** Accepted
**Date:** 2026-04-20
**Decision Makers:** Gabriel Mendoza

## Context
To ensure the SMT can scale horizontally and handle thousands of concurrent traffic events, the services must be designed according to cloud-native principles. We evaluated how to manage application state and configuration.

## Decision
The system adopts a **strictly stateless process model** (12-Factor Factor VI) and **externalized configuration** (Factor III).

## Rationale
1.  **Horizontal Scalability:** By keeping services stateless, we can spin up multiple instances of the `stream-processor` or `iot-gateway` behind a load balancer (or Kafka consumer groups) without worrying about session persistence or local data corruption.
2.  **Environment Parity:** Using `pydantic-settings` to read environment variables ensures that the same code artifact can run in Dev, Test, and Prod (Azure) just by changing the `.env` file.
3.  **Disposability:** Stateless services can be killed and restarted instantly, which is critical for CI/CD and automated recovery.

## Consequences
**Positive:**
- Zero "stickiness" requirements for scaling.
- Configuration is decoupled from the code.
- Simplified disaster recovery (just restart the container).

**Negative:**
- Requires external backing services for any persistence (Kafka/Mocks).
- Increased network overhead as state must be fetched or pushed to external stores.
