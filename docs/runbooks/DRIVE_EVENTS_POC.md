# DRIVE_EVENTS_POC.md — CAPITAL INDEX 2026

## Goal

Confirm whether Drive events for the test folder can reach Pub/Sub and whether Workspace Events API is usable as primary ingestion for CAPITAL INDEX.

## Test folder

```text
name: CAPITAL_INDEX_EVENT_TEST
folder_id: 1YHJ0YY4I_8QulKJR2O5S972_BK93NqMu
```

## Pub/Sub

```text
topic: capital-events-drive-test
subscription: capital-events-drive-test-sub
project: capital-index-2026
```

## Current baseline

```text
GCP project: capital-index-2026
Firestore: (default), eur3, FIRESTORE_NATIVE, STANDARD
Firebase rules: locked
Workspace APIs: enabled
Pub/Sub topic/subscription: created
Workspace reader SA: capital-workspace-reader@capital-index-2026.iam.gserviceaccount.com
Vault writer SA: capital-vault-writer@capital-index-2026.iam.gserviceaccount.com
```

## Current result

```text
Workspace Events API: paused
Drive Changes API fallback: verified
Decision record: docs/adr/0002-drive-ingestion-mode.md
Canonical probe script: scripts/drive_changes_probe.py
```

Observed probe runs:

```text
tests/fixtures/drive-events/probe_20260526T105500Z.json
changes: 0
folder_changes: 0
folder_children: 0

tests/fixtures/drive-events/probe_20260526T105738Z.json
changes: 5
folder_changes: 1
folder_children: 1
```

`.page_token.json` is local operational state and must not be committed.

Normalized event identity:

```text
gcp_project_id: capital-index-2026
project_id: capital_index
source_registry_id: drive_event_test
```

Do not use the GCP project id as the business `project_id`.

## Manual test events

Create the following files inside the test folder:

```text
01-created-doc
02-updated-doc
03-moved-doc
04-deleted-doc
```

Expected event categories:

```text
create
update
move
remove/delete
```

## Pull messages from Pub/Sub

```powershell
gcloud pubsub subscriptions pull capital-events-drive-test-sub `
  --project=capital-index-2026 `
  --limit=10 `
  --auto-ack
```

## Pass criteria

```text
1. Events arrive in Pub/Sub.
2. Payload includes usable resource identity.
3. Latency is acceptable for operational ingestion.
4. Subscription renewal/expiration behavior is understood.
```

## Fail behavior

If Workspace Events API does not produce usable Drive events for the target folder, use:

```text
Drive API changes.watch + changes.list
```

as the primary ingestion path.

For Phase 0.1, use Drive API `changes.getStartPageToken` and `changes.list`
polling/reconciliation as the working ingestion path. Revisit Workspace Events API
only after its auth/app ownership requirements are verified.

Production page token state must move to Firestore:

```text
/system_state/drive_changes/{source_registry_id}
```

## Output artifacts

Save captured payloads under:

```text
tests/fixtures/drive-events/
```

Create ADR if fallback is required:

```text
docs/adr/0002-drive-ingestion-mode.md
```
