# ADR-004: Orchestration via Docker Compose

**Status:** Accepted
**Date:** 2026-04-20
**Decision Makers:** Gabriel Mendoza

## Context
The SMT requires a reproducible environment for development, testing, and simulation across different developer machines and the target Azure VM. While Kubernetes (K8s) is the industry standard for production orchestration, the current project scope (simulation) requires a balance between operational simplicity and architectural alignment with cloud-native principles.

## Decision
We chose **Docker Compose** as the primary orchestration tool for the simulation environment.

## Rationale
1.  **Lower Operational Overhead:** Docker Compose allows the entire stack (8+ containers) to be managed with a single command without the complexity of Ingress controllers, PVCs, or Helm charts required by K8s.
2.  **Resource Efficiency:** Docker Compose is significantly lighter on CPU/RAM than a local K8s cluster (like Minikube or Kind), which is critical for developers running the YOLO detection dashboard locally.
3.  **Architectural Alignment:** The system is designed to be "K8s-ready". Every service is stateless and binds to a port, making the transition from Compose to K8s a matter of manifest configuration, not code changes.

## Consequences
**Positive:**
- Fast developer onboarding (single `docker compose up`).
- Consistent execution between local dev and the Azure Ubuntu VM.
- Simplified service discovery via the internal Docker network.

**Negative:**
- No automated horizontal pod autoscaling (HPA) in the simulation.
- Manual recovery if a container crashes (no K8s self-healing control plane).
- Shared resources on a single node (potential for noisy neighbor issues).
