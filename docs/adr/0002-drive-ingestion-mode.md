# ADR 0002 - Drive ingestion mode

## Status

Accepted for Phase 0.1.

## Context

CAPITAL INDEX needs a reliable Drive ingestion path for the `CAPITAL_INDEX_EVENT_TEST` folder before building the event fabric.

Workspace Events API was tested first, but the subscription path is paused:

```text
user token: INVALID_PUBSUB_TOPIC due to token/app project mismatch
DWD token: TARGET_RESOURCE_ACCESS_DENIED for the Drive target resource
```

The project must keep moving without depending on unresolved Workspace Events auth behavior.

## Decision

Use Drive API `changes.getStartPageToken` and `changes.list` polling as the Phase 0.1 fallback ingestion path.

Workspace Events API remains a future option after its exact auth, app ownership and target-resource requirements are verified.

Normalized events must separate infrastructure project identity from business project identity:

```text
gcp_project_id: GCP/Firebase project, for example capital-index-2026
project_id: CAPITAL INDEX business/control-plane project, resolved through source_registry/folder_policies
```

For the Phase 0.1 test folder:

```text
gcp_project_id: capital-index-2026
project_id: capital_index
source_registry_id: drive_event_test
```

`source_registry_id` is a resolved event field. It may default to `drive_event_test`
for the local POC fixture, but production ingestion must resolve it from
`source_registry` / `folder_policies` using the Drive folder id or parent chain.

`metadata-loader` should trust normalized event payload fields for base routing
and idempotency:

```text
file_id
name
mime_type
parents
modified_time
web_view_link
gcp_project_id
project_id
source_registry_id
```

It should re-fetch Drive metadata for authoritative and missing fields:

```text
owners
revision_id / headRevisionId where available
Drive Labels
capabilities
permissions summary if needed
```

Drive Changes API does not reliably distinguish create from update. The first
metadata-loader implementation must perform an upsert into `/files/{file_id}`.
If `/files/{file_id}` does not exist, the operation is a create; otherwise it is
an update.

Page token persistence for production polling must be stored in Firestore, not
in local files:

```text
/system_state/drive_changes/{source_registry_id}
  page_token
  previous_page_token
  updated_at
  lease_owner
  lease_expires_at
```

The polling worker must advance the token atomically after successful event
normalization and audit write.

## Evidence

Probe script:

```text
scripts/drive_changes_probe.py
```

Test folder:

```text
name: CAPITAL_INDEX_EVENT_TEST
folder_id: 1YHJ0YY4I_8QulKJR2O5S972_BK93NqMu
```

First run initialized the page token and wrote:

```text
tests/fixtures/drive-events/probe_20260526T105500Z.json
changes: 0
folder_changes: 0
folder_children: 0
```

After creating a test file in the folder, the second run wrote:

```text
tests/fixtures/drive-events/probe_20260526T105738Z.json
changes: 5
folder_changes: 1
folder_children: 1
```

## Consequences

Phase 1 event ingestion should start with a polling/reconciliation worker that:

```text
1. Stores and advances a Drive page token outside git.
2. Normalizes Drive changes into internal event records.
3. Uses idempotency keys per file/change token.
4. Writes raw payload references for audit.
5. Routes unknown folder/project/sensitivity cases to review_queue.
```

The local `.page_token.json` file is ignored because it is operational state, not a stable test fixture.

## Follow-up

Create the first `event-ingestor` implementation against saved Drive Changes fixtures before introducing Cloud Run or Pub/Sub deployment.
