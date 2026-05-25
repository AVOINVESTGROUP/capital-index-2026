# ADR 0001 — Repository-first implementation

## Status

Accepted

## Context

CAPITAL INDEX 2026 is a production-grade architecture with multiple GCP services, workers, registries and AI context projections.

Starting directly in GCP without repository documentation would create unmanaged configuration drift.

## Decision

Start with repository and documentation baseline before infrastructure implementation.

## Consequences

- Architecture has a stable source-controlled baseline.
- All next steps are logged in `docs/STEPS.md`.
- Implementation can proceed through clear phases.
