# AI Operating Instructions — CAPITAL INDEX 2026

## Purpose

This document defines how AI agents and operators work inside CAPITAL INDEX 2026.

## Source hierarchy

```text
1. Human approval and decision log
2. Firestore operational state
3. BigQuery audit/history
4. Original Google Workspace sources
5. Generated Vault projections
6. AI context bundles
7. AI summaries
```

AI output is never source of truth.

## Core rules

```text
Policy before content.
Metadata before extraction.
Review before restricted access.
Evidence before relationship creation.
Projection before AI consumption.
Audit for every AI call.
No silent assumptions.
```

## Vault rules

The Vault is a readable projection, not the database.

Generated content must use protected blocks:

```markdown
<!-- CAPITAL_INDEX:START:section_id:v1 -->
Generated content
<!-- CAPITAL_INDEX:END:section_id:v1 -->
```

Manual notes must not be overwritten.

## Confidence thresholds

```text
classification_auto_apply: >= 0.85
classification_review: 0.60–0.85
classification_reject: < 0.60
entity_accept: >= 0.70
relationship_accept: >= 0.75
dedupe_canonical_auto: >= 0.95
projection_publish: >= 0.80
```

## Context budgets

```text
AI_EXECUTIVE_CONTEXT.md: 30 KB
AI_PROJECT_INDEX.md: 50 KB
AI_RELATIONSHIP_GRAPH.md: 50 KB
AI_RECENT_CHANGES_7D.md: 30 KB
AI_REVIEW_QUEUE.md: 30 KB
```

If the limit is exceeded, keep blockers, risks, review items and active projects first. Paginate the rest.

## AI roles

```text
orchestrator: routes work and prepares decisions
auditor: checks architecture, policy, cost and quality
operator: executes allowed actions
summarizer: compresses context
relationship_analyst: finds graph links
human: final approval authority
```

## Required review cases

```text
unknown sensitivity
low confidence
project assignment conflict
possible duplicate
Vault projection conflict
restricted context request
high cost event
worker failure
DLQ event
```

## Commit discipline

```text
small commits
clear messages
docs updated with implementation steps
no untracked operational changes
```
