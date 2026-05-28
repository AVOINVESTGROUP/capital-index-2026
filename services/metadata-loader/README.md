# metadata-loader

Phase 1 worker for turning normalized Drive events into `/files/{file_id}`
upserts.

Current scope:

```text
input: normalized CAPITAL INDEX event batch
output: file metadata upsert payload batch
Cloud Run: POST /load-drive-metadata and POST /pubsub/metadata
Firestore: /files/{file_id}, gated by WRITE_ENABLED=true
Drive API refetch: gated by DRIVE_REFETCH_ENABLED=true
Next job: capital.jobs.policy, gated by PUBLISH_POLICY_JOBS=true
```

The worker writes to Firestore only when `WRITE_ENABLED=true`.
It calls Drive API only when `DRIVE_REFETCH_ENABLED=true`. It trusts the base
fields already present in the normalized event, then can refetch authoritative
fields before writing `/files/{file_id}`.
It publishes policy jobs only when `PUBLISH_POLICY_JOBS=true`.

## Contract

Trusted from normalized event:

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

Pending authoritative refetch:

```text
owners
head_revision_id
drive_labels
capabilities
permissions_summary
```

When Drive refetch is enabled and succeeds:

```text
metadata_status: authoritative_loaded
authoritative_refetch_status: loaded
```

When `WRITE_ENABLED=true` and `PUBLISH_POLICY_JOBS=true`, the metadata batch is
published to `capital.jobs.policy` after the `/files` write succeeds.

Drive Changes API does not reliably distinguish create from update, so this
worker emits:

```text
operation: upsert
```

## Run locally

```powershell
python services/metadata-loader/src/load_drive_metadata.py `
  tests/fixtures/drive-events/normalized_probe_20260526T105738Z.json
```

Write output to a file:

```powershell
python services/metadata-loader/src/load_drive_metadata.py `
  tests/fixtures/drive-events/normalized_probe_20260526T105738Z.json `
  --output tests/fixtures/drive-events/file_metadata_probe_20260526T105738Z.json
```

## Test

```powershell
python -m unittest `
  services/metadata-loader/tests/test_load_drive_metadata.py `
  services/metadata-loader/tests/test_firestore_writer.py `
  services/metadata-loader/tests/test_pubsub.py `
  services/metadata-loader/tests/test_drive_refetch.py `
  services/metadata-loader/tests/test_job_publisher.py
```
