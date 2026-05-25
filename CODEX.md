# CODEX.md — CAPITAL INDEX 2026

## Role

Codex or coding agents are used for implementation tasks inside CAPITAL INDEX 2026.

Coding agents must operate from repository state, not from memory.

## Required inputs

Before coding, a coding agent must read:

```text
README.md
docs/ARCHITECTURE.md
docs/STEPS.md
docs/ROADMAP.md
AGENTS.md
GEMINI.md
CHATGPT.md
CLAUDE.md
CODEX.md
docs/SKILLS.md
docs/QUALITY_GATES.md
```

## Implementation rules

```text
small pull requests
one subsystem per PR
tests or fixtures with each worker
no secrets in code
no hardcoded model IDs
no hardcoded folder paths without registry config
idempotency for workers
structured logs
trace_id on every event
```

## Worker requirements

Every worker must implement:

```text
input schema validation
output schema validation
idempotency key
retry-safe behavior
policy check where applicable
audit event
error route to DLQ or review_queue
```

## Required files per service

Each service directory must include:

```text
README.md
src/
tests/
Dockerfile
service.yaml or deployment config
schemas/
```

## Stop conditions

Do not proceed if:

```text
schema is missing
policy behavior is unclear
sensitivity class is unknown
secret is required but absent from Secret Manager
source registry is undefined
```
