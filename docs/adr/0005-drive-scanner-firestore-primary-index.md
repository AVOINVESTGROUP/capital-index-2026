# ADR-0005: Drive Scanner and Firestore as Primary File Index

Date: 2026-05-29

## Status

Accepted

## Context

CAPITAL INDEX needs a reliable, inspectable and correctable knowledge pipeline
over Google Drive and Google Workspace.

The legacy `CAPITAL_INDEX_2026` Google Sheet and Apps Script path proved useful
for migration and operator diagnostics, but it has production limitations:

- Apps Script runtime limits make broad Drive scans fragile;
- Sheet state is invisible to deployed workers until imported;
- Admin Web, review queues, extraction workers and context bundles read Firestore;
- a spreadsheet cannot be the long-term backend queue or source of truth;
- AI classification in a Sheet does not automatically create approved knowledge.

Google Drive is also noisy. Raw Drive inventory may contain drafts, duplicates,
stale files, prompts, generated snapshots, empty files and restricted content.
Therefore the primary index must support governance fields, manual overrides,
audit records and review routing.

## Decision

Cloud Run Drive Scanner writes the primary file inventory to Firestore:

```text
Google Drive
  -> capital-drive-scanner
  -> Firestore /files/{file_id}
```

Firestore `/files` is the operational source of truth for deployed workers and
Admin Web.

The Sheet path remains allowed only as:

- migration evidence;
- manual operator dashboard;
- diagnostic fallback;
- emergency one-file or recent-file sync path.

It is not the production database and not the backend queue.

## Production Flow

```text
Drive files
  -> Drive Scanner metadata upsert
  -> /files source-quality defaults
  -> AI classifier proposal fields
  -> Admin Web inspection and correction
  -> Policy Engine approval
  -> full text extraction
  -> facts/entities/relationships
  -> context bundles
  -> Obsidian and AI Gateway projections
```

## AI Authority Boundary

AI may propose:

```text
ai_proposed_project_id
ai_proposed_type
ai_summary
ai_value_score
ai_action
ai_sensitivity
ai_confidence
ai_evidence_file_ids
ai_provider_id
ai_model_id
```

AI may not directly approve:

```text
source_status = active
index_eligible = true
restricted read access
Drive mutation
archive/move/delete
context publication
```

Authoritative fields are written by policy-approved automation or human operator
actions:

```text
project_id
type
source_status
index_eligible
manual_override
approved_by
approved_at
human_block
```

## Operator Control Surface

Admin Web must provide:

- Source Files control for `/files`;
- AI proposal review and correction;
- Cleanup Queue recommendations and audit;
- Knowledge item inspection for extracted text and AI findings;
- Context bundle preview before publication;
- links back to Google Drive evidence files.

Every correction must preserve audit fields:

```text
actor_id
actor_type
previous_value
new_value
reason
note
created_at
source
```

## Context Bundle Model

AI Gateway must not load the whole Drive into a model context. It receives
controlled bundles assembled from Firestore and approved sources.

Required bundle types:

```text
owner_profile
project_context
relationship_graph
recent_changes
evidence_bundle
review_queue
risk_bundle
```

Evidence bundles must support multiple source files per answer. Drive links are
evidence and drill-down targets; the main knowledge should come from extracted
text, facts, entities and relationships in Firestore.

## Implementation Consequences

- Expand `capital-drive-scanner` beyond the single-root, 250-file MVP.
- Persist scan state and page tokens in Firestore.
- Preserve manual source-quality overrides during scanner refresh.
- Add AI classifier worker that reads `/files` and writes proposal fields.
- Add Admin Web actions to accept, correct or reject proposals.
- Keep content extraction blocked unless:

```text
source_status = active
index_eligible = true
policy_allowed = true
human_block = false
```

- Keep Sheet import optional and dry-run by default.
- Keep hard deletion forbidden.

## Non-Goals

This ADR does not approve:

- automatic Drive deletion;
- automatic archive/move without human approval;
- unrestricted AI reads of the whole Drive;
- using Sheet as production source of truth;
- publishing context bundles without policy/human controls.

## Supersedes

This ADR supersedes ADR-0004 where ADR-0004 treated the legacy Sheet as the
primary curated source for the first production migration.
