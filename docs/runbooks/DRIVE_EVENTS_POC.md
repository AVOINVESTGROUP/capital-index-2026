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

## Output artifacts

Save captured payloads under:

```text
tests/fixtures/drive-events/
```

Create ADR if fallback is required:

```text
docs/adr/0002-drive-ingestion-mode.md
```
