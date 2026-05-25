# Skills Catalog — CAPITAL INDEX 2026

## Purpose

This file defines the initial skills required for CAPITAL INDEX workers, AI agents and human operators.

## Skill format

Each skill must define:

```text
name
owner worker / agent
input
output
policy requirements
failure behavior
audit fields
```

## Core skills

### drive_event_ingestion

Owner:

```text
event-ingestor
```

Input:

```text
Drive event payload
```

Output:

```text
/events record
/jobs record
```

Rules:

```text
idempotency required
trace_id required
raw payload stored in audit path
```

### metadata_loading

Owner:

```text
metadata-loader
```

Input:

```text
file_id / resource_id
```

Output:

```text
/files update
/file_revisions update
```

Rules:

```text
read metadata only
no content extraction
transactional update
```

### policy_decision

Owner:

```text
policy-engine-worker
```

Input:

```text
metadata
folder policy
Drive Label
source registry
project registry
```

Output:

```text
allowed_actions
denied_actions
sensitivity_class
review_required
```

Rules:

```text
policy before content
SECRET and DO_NOT_INDEX block content reads
```

### content_extraction

Owner:

```text
content-extractor
```

Input:

```text
file_id
allowed_actions includes read_content
```

Output:

```text
/artifacts extraction artifact
/chunks if text is chunkable
```

Rules:

```text
must include source_revision_id
must include extraction method
```

### entity_extraction

Owner:

```text
entity-extractor
```

Input:

```text
chunks or extracted text
```

Output:

```text
/entities
/artifacts entity_extraction
```

Targets:

```text
people
companies
clients
suppliers
vehicles
money
dates
deadlines
risks
obligations
```

### relationship_extraction

Owner:

```text
relationship-extractor
```

Input:

```text
entities
project context
source evidence
```

Output:

```text
/relationships
```

Rules:

```text
relationship_accept >= 0.75
source evidence required
```

### vault_projection

Owner:

```text
vault-writer
```

Input:

```text
project state
relationships
recent changes
review queue
```

Output:

```text
Vault markdown projections
```

Rules:

```text
protected blocks only
backup before write
manual_override respected
```

### context_publishing

Owner:

```text
context-publisher
```

Input:

```text
Firestore graph
review queue
recent events
policy snapshot
```

Output:

```text
AI context bundles
```

Rules:

```text
provider-neutral
size budget enforced
restricted content excluded
```

### review_orchestration

Owner:

```text
review-orchestrator
```

Input:

```text
low confidence
policy conflict
projection conflict
restricted request
```

Output:

```text
/review_queue item
approval request
```

Rules:

```text
AI cannot approve its own action
human approval required for restricted/destructive actions
```
