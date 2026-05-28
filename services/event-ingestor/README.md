# event-ingestor

Phase 1 worker for normalizing source events into CAPITAL INDEX internal event
records.

Current scope:

```text
input: Drive Changes API probe fixture or Pub/Sub push envelope
output: normalized CAPITAL INDEX event JSON
Firestore: /events/{event_id}, gated by WRITE_ENABLED=true
Next job: capital.jobs.metadata, gated by PUBLISH_METADATA_JOBS=true
```

The worker writes to Firestore only when `WRITE_ENABLED=true`.
It publishes metadata jobs only when `PUBLISH_METADATA_JOBS=true`.

## Run locally

```powershell
python services/event-ingestor/src/normalize_drive_changes.py `
  tests/fixtures/drive-events/probe_20260526T105738Z.json
```

Write output to a file:

```powershell
python services/event-ingestor/src/normalize_drive_changes.py `
  tests/fixtures/drive-events/probe_20260526T105738Z.json `
  --output tests/fixtures/drive-events/normalized_probe_20260526T105738Z.json
```

## Test

```powershell
python -m unittest `
  services/event-ingestor/tests/test_normalize_drive_changes.py `
  services/event-ingestor/tests/test_firestore_writer.py `
  services/event-ingestor/tests/test_pubsub.py `
  services/event-ingestor/tests/test_job_publisher.py
```

## Cloud Run container

This first container target is write-disabled. It exposes:

```text
GET  /healthz
POST /normalize-drive-changes
POST /pubsub/drive-changes
```

The POST endpoint accepts the same Drive Changes probe payload shape used by
`tests/fixtures/drive-events/probe_*.json` and returns a normalized event batch.
The Pub/Sub endpoint accepts a standard Pub/Sub push envelope where
`message.data` is base64-encoded JSON with that same payload shape.

Firestore writes and downstream metadata jobs are controlled by:

```text
WRITE_ENABLED=false
PUBLISH_METADATA_JOBS=false
METADATA_JOBS_TOPIC=capital.jobs.metadata
```

When disabled, the response includes a dry-run `write` summary and no Firestore
client is created. When explicitly set to `true`, normalized events are upserted
to:

```text
/events/{event_id}
```

When `WRITE_ENABLED=true` and `PUBLISH_METADATA_JOBS=true`, the normalized batch
is published to `capital.jobs.metadata` after the `/events` write succeeds.

Build image:

```powershell
gcloud builds submit services/event-ingestor `
  --tag europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/event-ingestor:latest `
  --project capital-index-2026
```

Deploy authenticated Cloud Run service:

```powershell
gcloud run services replace services/event-ingestor/service.yaml `
  --region europe-west1 `
  --project capital-index-2026
```

## Event requirements

Each normalized event includes:

```text
event_id
trace_id
idempotency_key
source
source_event_type
event_type
observed_at
file_id
project_id
raw_payload_ref
next_action
review_required
```
