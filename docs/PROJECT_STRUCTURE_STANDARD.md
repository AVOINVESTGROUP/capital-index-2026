# Project Structure Standard — CAPITAL INDEX 2026

## Purpose

Every strategic project, product vertical, worker group or AI subsystem must have a predictable documentation and operating structure.

The system must not wait for a human to ask where AGENTS, GEMINI, skills or quality gates are.

## Repository root required files

```text
README.md
AGENTS.md
GEMINI.md
CLAUDE.md
CHATGPT.md
CODEX.md
.env.example
.gitignore
```

## Documentation required files

```text
docs/ARCHITECTURE.md
docs/STEPS.md
docs/ROADMAP.md
docs/AI_CONTEXT.md
docs/SKILLS.md
docs/QUALITY_GATES.md
docs/PROJECT_STRUCTURE_STANDARD.md
docs/INTAKE_PROTOCOL.md
docs/adr/
docs/runbooks/
docs/schemas/
```

## Service required structure

Each service must have:

```text
services/{service_name}/README.md
services/{service_name}/src/
services/{service_name}/tests/
services/{service_name}/schemas/
services/{service_name}/Dockerfile
```

## New idea required structure

Every captured idea must be converted into:

```text
id
title
type
status
priority
linked_projects
source
strongest_version
weakest_point
dependencies
first_validation_step
next_action
open_questions
```

## New subsystem required artifacts

For every new subsystem create or update:

```text
architecture section
worker or agent definition
skill definition
schema definition
roadmap item
GitHub issue
quality gate if needed
```

## Required project statuses

```text
captured
queued
research_required
blocked_dependency
implementation_ready
active
paused
archived
```

## Required priority scale

```text
critical
high
medium
low
archive
```
