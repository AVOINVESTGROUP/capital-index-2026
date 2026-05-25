# Intake Protocol — CAPITAL INDEX 2026

## Purpose

This protocol defines how CAPITAL INDEX captures, evaluates and routes new ideas, corrections, files, projects and operational signals.

The goal is to prevent passive note storage.

## Intake types

```text
idea
project_task
architecture_change
bug
risk
source_file
relationship_signal
business_opportunity
user_correction
policy_exception
```

## Required fields

Every intake item requires:

```text
id
type
title
source
created_at
status
priority
linked_projects
linked_entities
confidence
next_action
```

## Routing statuses

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

## User correction handling

A user correction is not only a chat reply. It must produce one of:

```text
quality gate
operating instruction
agent rule
skill update
architecture correction
issue
ADR
```

Examples:

```text
wrong path assumption → update QUALITY_GATES.md
missing GEMINI.md → create GEMINI.md and update PROJECT_STRUCTURE_STANDARD.md
missing AGENTS.md → create AGENTS.md and update PROJECT_STRUCTURE_STANDARD.md
passive idea handling → update INTAKE_PROTOCOL.md and QUALITY_GATES.md
```

## Idea processing checklist

For every non-trivial idea:

```text
1. Assign ID.
2. Link to projects.
3. Extract core thesis.
4. Create strongest version.
5. Identify weakest point.
6. Identify dependencies.
7. Identify first validation step.
8. Define one next action.
9. Add to queue.
10. Create/update repository artifact.
```

## Cross-project scan

Check every idea against:

```text
CAPITAL INDEX
100Trust
MindShare
Integra Motors
Fresh Cuisine
Content Factory
AVOuniverse
existing GCP/Firebase projects
Vault areas
```

## Output formats

For GitHub:

```text
issue
ADR
docs update
project artifact
```

For Vault:

```text
strategic opportunity note
project overview update
review queue item
```

For Firestore later:

```text
/intake_items/{item_id}
/review_queue/{review_id}
/projects/{project_id}
/relationships/{relationship_id}
```

## Hard rule

No idea remains only in conversation.
