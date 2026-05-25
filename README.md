# CAPITAL INDEX 2026

Production-grade central intelligence layer for Google Workspace, GCP/Firebase projects, Obsidian Vault and AI context bundles.

## Purpose

CAPITAL INDEX 2026 is a control plane, event bus, AI processing fabric, knowledge graph and projection system.

It is designed to:

1. Track changes across Google Drive, Gmail, Sheets, Docs, Calendar and selected GCP/Firebase projects.
2. Classify files and records by project, business, sensitivity and data domain.
3. Extract entities, relationships, risks, deadlines, financial signals and operational facts.
4. Build a cross-project knowledge graph.
5. Publish safe projections to Obsidian Vault, Sheets dashboard and universal AI context bundles.
6. Support multiple AI providers through a provider-neutral AI Gateway.

## Current phase

Repository and documentation foundation.

## Initial implementation order

1. Repository documentation and architecture baseline.
2. GCP project `capital-index-2026`.
3. Drive Events POC.
4. Pub/Sub event fabric.
5. Metadata ingestion.
6. Policy engine.
7. Registry import.
8. Context publishing.

## Repository layout

```text
docs/
  ARCHITECTURE.md
  STEPS.md
  ROADMAP.md
  AI_CONTEXT.md
  adr/
  runbooks/
  schemas/

infra/
  terraform/

services/
  event-ingestor/
  metadata-loader/
  policy-engine-worker/
  context-publisher/

scripts/
tests/
```

## Rules

- Firestore is operational source of truth.
- BigQuery is audit, history and analytics.
- Google Drive contains source files.
- Obsidian Vault is projection only.
- Sheets dashboard is not a database.
- Apps Script is not backend queue.
- AI is not source of truth.
- No automatic deletion.
- No AI access to `SECRET` or `DO_NOT_INDEX`.
