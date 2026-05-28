# policy-engine-worker

Phase 2 worker for applying CAPITAL INDEX policy decisions to file metadata
upsert payloads.

Current scope:

```text
input: file metadata upsert batch or Pub/Sub push envelope
output: policy decision batch
Cloud Run: POST /apply-policy and POST /pubsub/policy
Firestore: /policy_decisions/{decision_id}, gated by WRITE_ENABLED=true
Next job: capital.jobs.extraction, gated by PUBLISH_EXTRACTION_JOBS=true
```

The worker writes to Firestore only when `WRITE_ENABLED=true`.
It publishes extraction jobs only when `PUBLISH_EXTRACTION_JOBS=true`.
It uses a local copy of the seeded POC policies from
`scripts/seed_firestore_baseline.py`.

## POC policy

For `source_registry_id = drive_event_test`:

```text
sensitivity_class: PUBLIC_INTERNAL
allowed_actions:
  read_metadata
  read_content
denied_actions:
  embed
  publish_to_vault
  include_in_ai_context
review_required: false
```

Unknown sources use the default locked policy:

```text
sensitivity_class: UNCLASSIFIED_REVIEW_REQUIRED
allowed_actions:
  read_metadata
denied_actions:
  read_content
  summarize
  embed
  publish_to_vault
  include_in_ai_context
review_required: true
```

## Run locally

```powershell
python services/policy-engine-worker/src/apply_policy.py `
  tests/fixtures/drive-events/file_metadata_probe_20260526T105738Z.json
```

Write output to a file:

```powershell
python services/policy-engine-worker/src/apply_policy.py `
  tests/fixtures/drive-events/file_metadata_probe_20260526T105738Z.json `
  --output tests/fixtures/drive-events/policy_decision_probe_20260526T105738Z.json
```

## Test

```powershell
python -m unittest `
  services/policy-engine-worker/tests/test_apply_policy.py `
  services/policy-engine-worker/tests/test_firestore_writer.py `
  services/policy-engine-worker/tests/test_pubsub.py `
  services/policy-engine-worker/tests/test_job_publisher.py
```
