# CAPITAL INDEX 2026 — Architecture

## 1. System definition

CAPITAL INDEX 2026 is a production-grade central intelligence layer over Google Workspace, GCP/Firebase projects, Obsidian Vault and AI context bundles.

It consists of:

```text
Control Plane
Event Bus
AI Processing Fabric
Knowledge Graph
Projection Layer
AI Gateway
Observability and Audit Layer
```

## 2. Source of truth

```text
Firestore = operational source of truth
BigQuery = audit, history, analytics
Google Drive = source files
Obsidian Vault = readable projection
Google Sheets = human dashboard
AI context files = compressed AI-facing projection
```

## 3. High-level architecture

```text
SOURCE LAYER
Drive | Gmail | Sheets | Docs | Calendar | Firebase | GCP
        ↓
EVENT LAYER
Workspace Events API | Drive API Watch | Gmail Push | Sheets Bridge | Scheduler | Pub/Sub
        ↓
CONTROL PLANE
Project Registry | Source Registry | Policy Engine | Identity Resolver | Job Orchestrator
        ↓
AI PROCESSING FABRIC
Classifier | Extractor | OCR | Chunker | Embedder | Entity Extractor | Relationship Extractor | Dedupe | Graph Builder | Validator
        ↓
STORAGE LAYER
Firestore | BigQuery | Cloud Storage | Secret Manager
        ↓
PROJECTION LAYER
Vault Writer | Context Publisher | Sheets Dashboard | Daily Briefing | Approval Channels
        ↓
CONSUMPTION LAYER
AI Gateway | Claude | Gemini | ChatGPT | Agents | Dashboards
```

## 4. First technical gate

Before full event fabric implementation, run:

```text
POC-DRIVE-EVENTS-001
```

Goal:

```text
Confirm that Drive create/update/move/delete events can reach Pub/Sub.
```

Primary path:

```text
Workspace Events API Drive subscriptions → Cloud Pub/Sub
```

Fallback:

```text
Drive API changes.watch + changes.list
```

## 5. Core collections

```text
/project_registry
/source_registry
/folder_policies
/files
/file_revisions
/artifacts
/chunks
/entities
/relationships
/projects
/people
/businesses
/jobs
/events
/review_queue
/approval_decisions
/security_policies
/dedupe_clusters
/projections
/ai_contexts
/decision_log
/cost_state
/system_config
/migration_runs
/migration_errors
/legacy_artifacts
```

## 6. Workers

```text
event-ingestor
metadata-loader
policy-engine-worker
classifier-worker
content-extractor
document-ai-worker
chunker-worker
embedder-worker
entity-extractor
relationship-extractor
dedupe-clusterer
graph-builder
validator-worker
vault-writer
context-publisher
sheets-dashboard-writer
review-orchestrator
ai-gateway
scoring-engine
cost-controller
audit-writer
dlq-reprocessor
```

## 7. AI Gateway principle

CAPITAL INDEX is provider-neutral.

It must support one or several AI executors at the same time:

```text
Claude
Gemini
ChatGPT
Vertex Model Garden
custom HTTP agents
local agents
human operator
```

AI cannot approve its own restricted actions, bypass policy, delete files or publish restricted context.
