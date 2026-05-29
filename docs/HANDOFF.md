# HANDOFF — CAPITAL INDEX 2026

## Purpose

This file is the transition note for continuing CAPITAL INDEX 2026 in another chat or with another AI/operator.

The next assistant must not guess prior state. Use this file as the current operational baseline.

---

## 1. Current project status

Repository created and pushed:

```text
GitHub: AVOINVESTGROUP/capital-index-2026
Local path: C:\Dev\capital_orc
Default branch: main
```

Current architectural decision:

```text
Primary production inventory path:
Google Drive -> Cloud Run capital-drive-scanner -> Firestore /files

Legacy path:
Apps Script + CAPITAL_INDEX_2026 Sheet is migration/operator aid only.

AI authority:
AI writes proposals. Policy Engine, Review Orchestrator or human approval writes
authoritative decisions.
```

Current immediate implementation direction:

```text
1. capital-drive-scanner now supports all_drive inventory mode and Scheduler
   uses {"write": true, "scan_mode": "all_drive", "max_files": 3000}.
2. Broad scan is metadata-only and keeps DRIVE_REFETCH_ENABLED=false by default.
3. Persist scan state/page tokens in Firestore.
4. Add Firestore-backed AI classifier proposal fields.
5. Use Admin Web as the correction/control surface.
6. Build context bundles from approved Firestore state, extracted text, facts,
   entities and relationships.
```

GCP project exists:

```text
project_id: capital-index-2026
project_number: 745677061768
organization: fixer.guru
```

Firebase / Firestore created correctly:

```text
Firebase project: capital-index-2026
Firestore database: (default)
Firestore location: eur3
Firestore type: FIRESTORE_NATIVE
Firestore edition: STANDARD
```

Firestore rules/indexes deployed:

```text
firestore.rules: locked baseline
firestore.indexes.json: empty baseline
```

Initial Firestore seed completed successfully.

---

## 2. Repository files already created

Root AI/operator files:

```text
AGENTS.md
GEMINI.md
CLAUDE.md
CHATGPT.md
CODEX.md
README.md
.env.example
.gitignore
firebase.json
.firebaserc
firestore.rules
firestore.indexes.json
requirements.txt
```

Docs:

```text
docs/ARCHITECTURE.md
docs/STEPS.md
docs/ROADMAP.md
docs/AI_CONTEXT.md
docs/AI_OPERATING_INSTRUCTIONS.md
docs/SKILLS.md
docs/QUALITY_GATES.md
docs/PROJECT_STRUCTURE_STANDARD.md
docs/INTAKE_PROTOCOL.md
docs/SECRETS_POLICY.md
docs/runbooks/FIREBASE_BASELINE.md
docs/runbooks/DRIVE_EVENTS_POC.md
```

Scripts:

```text
scripts/seed_firestore_baseline.py
scripts/create_workspace_drive_subscription.py
scripts/drive_changes_probe.py
```

Fixtures:

```text
tests/fixtures/drive-events/.gitkeep
```

---

## 3. Important policy decisions

### 3.1 Secrets

All real secrets must go to Google Secret Manager.

Policy document:

```text
docs/SECRETS_POLICY.md
```

Do not use service account JSON keys as the normal path.

Forbidden as source of truth:

```text
local secrets/ folder
repository
Vault
Google Sheets
Firestore
Apps Script Properties for production secrets
```

Preferred auth model:

```text
local dev: gcloud ADC + IAMCredentials signJwt
production: service account identity / Workload Identity / Secret Manager only where required
```

Admin web boundary:

```text
NEXT_PUBLIC_* values may be visible in the browser and must not contain secrets.
Server credentials, service account material, bot tokens and OAuth secrets must never enter the browser bundle.
Default admin web implementation should use Next server routes before direct Firestore browser writes.
```

### 3.2 Workspace Events status

Workspace Events POC is currently paused.

Verified:

```text
Pub/Sub topic exists
Google Drive system publisher binding fixed
User token has Drive scope
DWD service-account flow signs JWT and exchanges token
```

Still failing:

```text
Workspace Events subscription with user token:
  INVALID_PUBSUB_TOPIC
  reason: token/app project mismatch

Workspace Events subscription with DWD token:
  TARGET_RESOURCE_ACCESS_DENIED
  reason: Drive target resource access denied
```

Decision for now:

```text
Do not continue fighting Workspace Events auth.
Use Drive API changes.list / startPageToken polling as fallback POC path.
```

---

## 4. Google Workspace baseline

Test Drive folder created:

```text
name: CAPITAL_INDEX_EVENT_TEST
folder_id: 1YHJ0YY4I_8QulKJR2O5S972_BK93NqMu
url: https://drive.google.com/drive/folders/1YHJ0YY4I_8QulKJR2O5S972_BK93NqMu
```

Service accounts created:

```text
capital-workspace-reader@capital-index-2026.iam.gserviceaccount.com
capital-vault-writer@capital-index-2026.iam.gserviceaccount.com
firebase-adminsdk-fbsvc@capital-index-2026.iam.gserviceaccount.com
capital-event-ingestor@capital-index-2026.iam.gserviceaccount.com
capital-metadata-loader@capital-index-2026.iam.gserviceaccount.com
capital-policy-engine@capital-index-2026.iam.gserviceaccount.com
capital-content-extractor@capital-index-2026.iam.gserviceaccount.com
capital-drive-governance@capital-index-2026.iam.gserviceaccount.com
capital-entity-extractor@capital-index-2026.iam.gserviceaccount.com
```

Domain-Wide Delegation client IDs:

```text
capital-workspace-reader client_id: 105249244589764651440
capital-vault-writer client_id: 117734605799955226260
```

Reader scopes intended in Admin Console:

```text
https://www.googleapis.com/auth/drive.metadata.readonly
https://www.googleapis.com/auth/drive.readonly
https://www.googleapis.com/auth/spreadsheets.readonly
https://www.googleapis.com/auth/documents.readonly
https://www.googleapis.com/auth/gmail.readonly
```

Writer scope intended in Admin Console:

```text
https://www.googleapis.com/auth/drive.file
```

---

## 5. Enabled APIs

Enabled APIs observed:

```text
docs.googleapis.com
drive.googleapis.com
driveactivity.googleapis.com
firestore.googleapis.com
gmail.googleapis.com
iamcredentials.googleapis.com
pubsub.googleapis.com
sheets.googleapis.com
workspaceevents.googleapis.com
firebase.googleapis.com
firebaserules.googleapis.com
bigquery.googleapis.com
storage.googleapis.com
logging.googleapis.com
monitoring.googleapis.com
```

Billing is not yet attached, so these were blocked/deferred:

```text
run.googleapis.com
cloudbuild.googleapis.com
artifactregistry.googleapis.com
containerregistry.googleapis.com
```

Billing status:

```text
Billing is attached and enabled.
billingAccountName: billingAccounts/01806F-95B148-FFB4FF
Cloud Run / Cloud Build / Artifact Registry APIs are enabled.
Artifact repo: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers
Runbook: docs/runbooks/CLOUD_BASELINE.md
```

---

## 6. Firestore seeded documents

Seed script already run successfully:

```text
python scripts/seed_firestore_baseline.py
```

Seeded:

```text
/system_config/model_routing
/system_config/vector_backend
/system_config/throttling
/project_registry/capital_index
/source_registry/vault_root
/source_registry/drive_event_test
/security_policies/default_locked
/folder_policies/vault_root
/folder_policies/drive_event_test
```

---

## 7. Current GitHub issues

Issue #1:

```text
Phase 0.1 — Drive Events POC
Status: Workspace Events path paused; fallback Drive Changes probe is next.
```

Issue #2:

```text
Phase 0.2 — Firebase baseline setup
Status: Firestore created correctly in eur3, rules deployed, seed completed.
```

Issue #3:

```text
Phase 0.3 — Workspace baseline setup
Status: test folder created, service accounts created, DWD client IDs known.
```

---

## 8. Current next action

Drive Changes API probe completed successfully.

Observed fixtures:

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

Decision:

```text
Workspace Events API remains paused.
Drive API changes.getStartPageToken + changes.list is the Phase 0.1 fallback ingestion path.
ADR: docs/adr/0002-drive-ingestion-mode.md
```

Current next action:

```text
Implement Drive Governance MVP fixture-first before graph/entity extraction.
```

Local event-ingestor prototype is now present:

```text
services/event-ingestor/src/event_ingestor/drive_changes.py
services/event-ingestor/src/normalize_drive_changes.py
services/event-ingestor/schemas/normalized_drive_event.schema.json
services/event-ingestor/tests/test_normalize_drive_changes.py
tests/fixtures/drive-events/normalized_probe_20260526T105738Z.json
```

Verified:

```text
python -m unittest services/event-ingestor/tests/test_normalize_drive_changes.py
OK
```

Important event identity rule:

```text
gcp_project_id = infrastructure project, e.g. capital-index-2026
project_id = CAPITAL INDEX business/control-plane project, e.g. capital_index
source_registry_id = resolved source, e.g. drive_event_test
```

Do not write the GCP project id into `/files/{file_id}.project_id`.

Local metadata-loader prototype is now present:

```text
services/metadata-loader/src/metadata_loader/drive_metadata.py
services/metadata-loader/src/metadata_loader/drive_refetch.py
services/metadata-loader/src/metadata_loader/firestore_writer.py
services/metadata-loader/src/metadata_loader/job_publisher.py
services/metadata-loader/src/metadata_loader/pubsub.py
services/metadata-loader/src/metadata_loader/workspace_auth.py
services/metadata-loader/src/load_drive_metadata.py
services/metadata-loader/src/app.py
services/metadata-loader/Dockerfile
services/metadata-loader/service.yaml
services/metadata-loader/schemas/file_metadata_upsert.schema.json
services/metadata-loader/tests/test_load_drive_metadata.py
services/metadata-loader/tests/test_drive_refetch.py
services/metadata-loader/tests/test_firestore_writer.py
services/metadata-loader/tests/test_job_publisher.py
services/metadata-loader/tests/test_pubsub.py
tests/fixtures/drive-events/file_metadata_probe_20260526T105738Z.json
```

Verified:

```text
python -m unittest services/metadata-loader/tests/test_load_drive_metadata.py
OK
```

Metadata-loader contract:

```text
operation: upsert
metadata_status: base_loaded or authoritative_loaded
authoritative_refetch_status: pending or loaded
next_action: policy_check
```

Metadata-loader Cloud Run worker completed:

```text
service: capital-metadata-loader
region: europe-west1
image: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/metadata-loader:latest
revision: capital-metadata-loader-00006-v7p
ingress: all, authenticated only
WRITE_ENABLED: false
DRIVE_REFETCH_ENABLED: false
PUBLISH_POLICY_JOBS: false
POLICY_JOBS_TOPIC: capital.jobs.policy
WORKER_VERSION: metadata-loader-policy-e2e-verified
```

Metadata-loader endpoints:

```text
GET /healthz
POST /load-drive-metadata
POST /pubsub/metadata
```

Metadata-loader controlled write verified:

```text
document: /files/1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM
write_source: metadata-loader
firestore_schema_version: capital.files.v1
last_source_event_id: evt_888e52cfd457eb5c126b00bf
verified: true
```

Metadata-loader downstream policy job publishing completed:

```text
PUBLISH_POLICY_JOBS=false by default
POLICY_JOBS_TOPIC=capital.jobs.policy
When WRITE_ENABLED=true and PUBLISH_POLICY_JOBS=true:
  metadata-loader writes /files/{file_id}
  then publishes the metadata batch to capital.jobs.policy
```

Metadata-loader Pub/Sub push verified:

```text
subscription: capital.jobs.metadata.worker.push
topic: capital.jobs.metadata
push_endpoint: https://capital-metadata-loader-745677061768.europe-west1.run.app/pubsub/metadata
oidc_service_account: capital-metadata-loader@capital-index-2026.iam.gserviceaccount.com
published_message_id: 19644059606693559
Cloud Run status: 200
Firestore document: /files/1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM
updated_at: 2026-05-27T08:49:14+00:00
verified: true
```

Metadata-loader Drive API authoritative refetch verified:

```text
temporary revision: capital-metadata-loader-00010-5dz
temporary WRITE_ENABLED: true
temporary DRIVE_REFETCH_ENABLED: true
endpoint: POST /load-drive-metadata
document: /files/1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM
metadata_status: authoritative_loaded
authoritative_refetch_status: loaded
owner: office@integrayachtsuae.com
head_revision_id: 1
permissions_summary.total: 1
verified: true
```

Local policy-engine-worker prototype is now present:

```text
services/policy-engine-worker/src/policy_engine/decision.py
services/policy-engine-worker/src/policy_engine/firestore_writer.py
services/policy-engine-worker/src/policy_engine/pubsub.py
services/policy-engine-worker/src/apply_policy.py
services/policy-engine-worker/src/app.py
services/policy-engine-worker/Dockerfile
services/policy-engine-worker/service.yaml
services/policy-engine-worker/schemas/policy_decision.schema.json
services/policy-engine-worker/tests/test_apply_policy.py
services/policy-engine-worker/tests/test_firestore_writer.py
services/policy-engine-worker/tests/test_pubsub.py
tests/fixtures/drive-events/policy_decision_probe_20260526T105738Z.json
```

Verified:

```text
python -m unittest services/policy-engine-worker/tests/test_apply_policy.py
OK
```

Policy result for `drive_event_test`:

```text
sensitivity_class: PUBLIC_INTERNAL
allowed_actions: read_metadata, read_content
denied_actions: embed, publish_to_vault, include_in_ai_context
review_required: false
next_action: content_extraction_candidate
```

Policy-engine-worker Cloud Run worker completed:

```text
service: capital-policy-engine
region: europe-west1
image: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/policy-engine-worker:latest
revision: capital-policy-engine-00005-clw
ingress: all, authenticated only
WRITE_ENABLED: false
WORKER_VERSION: policy-engine-e2e-verified
```

Policy-engine-worker endpoints:

```text
GET /healthz
POST /apply-policy
POST /pubsub/policy
```

Policy-engine-worker Pub/Sub and Firestore write verified:

```text
subscription: capital.jobs.policy.worker.push
topic: capital.jobs.policy
push_endpoint: https://capital-policy-engine-745677061768.europe-west1.run.app/pubsub/policy
oidc_service_account: capital-policy-engine@capital-index-2026.iam.gserviceaccount.com
published_message_id: 19644335376522148
Cloud Run status: 200
Firestore document: /policy_decisions/policy_7f56e9fe6ddee8aff5f36794
verified: true
```

Metadata -> policy chain verified:

```text
input_topic: capital.jobs.metadata
input_message_id: 19644506911761063
metadata-loader endpoint: POST /pubsub/metadata
metadata-loader status: 200
policy-engine endpoint: POST /pubsub/policy
policy-engine status: 200
policy document: /policy_decisions/policy_7f56e9fe6ddee8aff5f36794
sensitivity_class: PUBLIC_INTERNAL
next_action: content_extraction_candidate
written_at: 2026-05-27T09:40:58+00:00
verified: true
```

Local content-extractor prototype and Docs API probe are now present:

```text
services/content-extractor/src/content_extractor/docs_reader.py
services/content-extractor/src/content_extractor/review_queue.py
services/content-extractor/schemas/extracted_text.schema.json
services/content-extractor/tests/test_docs_reader.py
services/content-extractor/tests/test_review_queue.py
scripts/docs_content_probe.py
tests/fixtures/docs/doc_response_20260526T105738Z.json
tests/fixtures/docs/doc_response_probe_20260526T105738Z.json
```

Verified:

```text
python scripts/docs_content_probe.py 1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM --output tests/fixtures/docs/doc_response_probe_20260526T105738Z.json
Docs API access OK
title: drive-probe-test-001
chars: 1
```

The live test Google Doc is effectively empty; extracted text is only a newline.
`content-extractor` correctly routes this case to `review_required`.

All current explicit service tests:

```text
python -m unittest services/event-ingestor/tests/test_normalize_drive_changes.py services/metadata-loader/tests/test_load_drive_metadata.py services/policy-engine-worker/tests/test_apply_policy.py services/content-extractor/tests/test_docs_reader.py
Ran 15 tests
OK
```

First Cloud Run worker deployed:

```text
service: capital-event-ingestor
region: europe-west1
ingress: internal
revision: capital-event-ingestor-00006-22k
image: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/event-ingestor:latest
WRITE_ENABLED: false
WORKER_VERSION: event-ingestor-write-boundary-v2
status: Ready
```

Event-ingestor Firestore write boundary:

```text
WRITE_ENABLED=false:
  dry-run only
  no Firestore client created

WRITE_ENABLED=true:
  upsert /events/{event_id}
```

Controlled Firestore write completed:

```text
event_id: evt_888e52cfd457eb5c126b00bf
document: /events/evt_888e52cfd457eb5c126b00bf
file_id: 1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM
project_id: capital_index
write_source: event-ingestor
firestore_schema_version: capital.events.v1
verified: true
```

The Cloud Run service was returned to safe mode after the test:

```text
revision: capital-event-ingestor-00006-22k
ingress: internal
WRITE_ENABLED: false
```

Event-ingestor Pub/Sub push execution model completed:

```text
subscription: capital.events.drive.ingestor.push
topic: capital.events.drive
push_endpoint: https://capital-event-ingestor-745677061768.europe-west1.run.app/pubsub/drive-changes
oidc_service_account: capital-event-ingestor@capital-index-2026.iam.gserviceaccount.com
published_message_id: 19644170894832603
Cloud Run status: 200
Firestore document: /events/evt_888e52cfd457eb5c126b00bf
raw_payload_ref: pubsub://message/19644170894832603#/folder_changes/0
verified: true
```

Event-ingestor downstream metadata job publishing completed:

```text
PUBLISH_METADATA_JOBS=false by default
METADATA_JOBS_TOPIC=capital.jobs.metadata
When WRITE_ENABLED=true and PUBLISH_METADATA_JOBS=true:
  event-ingestor writes /events/{event_id}
  then publishes the normalized batch to capital.jobs.metadata
```

End-to-end event -> metadata chain verified:

```text
input_topic: capital.events.drive
input_message_id: 19644990894445117
event-ingestor endpoint: POST /pubsub/drive-changes
event-ingestor status: 200
event document: /events/evt_888e52cfd457eb5c126b00bf
event raw_payload_ref: pubsub://message/19644990894445117#/folder_changes/0
event written_at: 2026-05-27T09:04:30+00:00
metadata-loader endpoint: POST /pubsub/metadata
metadata-loader status: 200
file document: /files/1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM
file updated_at: 2026-05-27T09:04:35+00:00
verified: true
```

Final Cloud Run safe state after Pub/Sub verification:

```text
revision: capital-event-ingestor-00016-zvk
ingress: all, authenticated only
WRITE_ENABLED: false
PUBLISH_METADATA_JOBS: false
WORKER_VERSION: event-ingestor-e2e-verified
```

Final metadata-loader safe state after policy e2e verification:

```text
revision: capital-metadata-loader-00014-hm4
ingress: all, authenticated only
WRITE_ENABLED: false
DRIVE_REFETCH_ENABLED: false
PUBLISH_POLICY_JOBS: false
WORKER_VERSION: metadata-loader-policy-e2e-verified
```

Final policy-engine safe state after policy e2e verification:

```text
revision: capital-policy-engine-00008-xh5
ingress: all, authenticated only
WRITE_ENABLED: false
PUBLISH_EXTRACTION_JOBS: false
WORKER_VERSION: policy-engine-extraction-e2e-verified
```

Policy-engine downstream extraction job publishing completed:

```text
PUBLISH_EXTRACTION_JOBS=false by default
EXTRACTION_JOBS_TOPIC=capital.jobs.extraction
When WRITE_ENABLED=true and PUBLISH_EXTRACTION_JOBS=true:
  policy-engine writes /policy_decisions/{decision_id}
  then publishes the policy decision batch to capital.jobs.extraction
```

Content-extractor Cloud Run worker completed:

```text
service: capital-content-extractor
region: europe-west1
image: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/content-extractor:latest
revision: capital-content-extractor-00003-dt2
ingress: all, authenticated only
WRITE_ENABLED: false
DOCS_READ_ENABLED: false
REVIEW_QUEUE_ENABLED: false
WORKER_VERSION: content-extractor-review-queue-verified
```

Content-extractor endpoints:

```text
GET /healthz
POST /extract-content
POST /pubsub/extraction
```

Content-extractor Pub/Sub and Firestore write verified:

```text
subscription: capital.jobs.extraction.worker.push
topic: capital.jobs.extraction
push_endpoint: https://capital-content-extractor-745677061768.europe-west1.run.app/pubsub/extraction
oidc_service_account: capital-content-extractor@capital-index-2026.iam.gserviceaccount.com
published_message_id: 19645499520482976
Cloud Run status: 200
Firestore document: /extracted_text/1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM
verified: true
```

Policy -> extraction chain verified:

```text
input_topic: capital.jobs.policy
input_message_id: 19645575446517248
policy-engine endpoint: POST /pubsub/policy
policy-engine status: 200
content-extractor endpoint: POST /pubsub/extraction
content-extractor status: 200
extracted document: /extracted_text/1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM
doc_title: drive-probe-test-001
char_count: 1
next_action: review_required
review_reason: empty_text
written_at: 2026-05-27T12:01:15+00:00
verified: true
```

Final content-extractor safe state after extraction e2e verification:

```text
revision: capital-content-extractor-00007-tv6
ingress: all, authenticated only
WRITE_ENABLED: false
DOCS_READ_ENABLED: false
SHEETS_READ_ENABLED: false
DRIVE_READ_ENABLED: false
REVIEW_QUEUE_ENABLED: false
WORKER_VERSION: content-extractor-multiformat
```

Content-extractor multi-format support added:

```text
Google Docs: Docs API
Google Sheets: Sheets API
Markdown/plain text: Drive API download
files:
  services/content-extractor/src/content_extractor/sheets_reader.py
  services/content-extractor/src/content_extractor/plain_text_reader.py
  services/content-extractor/tests/test_multiformat_extraction.py
fixture:
  tests/fixtures/docs/sheet_response_20260527.json
policy decision now carries:
  name
  mime_type
  web_view_link
verified:
  python -m unittest services/content-extractor/tests/test_docs_reader.py services/content-extractor/tests/test_multiformat_extraction.py services/policy-engine-worker/tests/test_apply_policy.py -v
  full explicit service suite: 42 tests OK
deployed:
  policy-engine revision: capital-policy-engine-00009-vq9
  policy-engine image: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/policy-engine-worker:multiformat-20260527
  content-extractor revision: capital-content-extractor-00007-tv6
  content-extractor image: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/content-extractor:multiformat-20260527
```

Controlled live multi-format extraction completed:

```text
candidate search script:
  scripts/drive_content_candidates.py
live extraction script:
  scripts/live_multiformat_extraction_probe.py

Markdown:
  file_id: 1xOOLBOLz-tpaz6w5lWORFNtMyWPQO86v
  title: 2026-05-27.md
  char_count: 236
  next_action: classify

Google Sheet:
  file_id: 1C72TfkF6ReGS9wTbewzqDW4NaK_omSy2l_ZmX1K-WQ0
  title: AI_Bridge_Log_Spreadsheet
  char_count: 209330
  next_action: classify

Firestore:
  /extracted_text/1xOOLBOLz-tpaz6w5lWORFNtMyWPQO86v
  /extracted_text/1C72TfkF6ReGS9wTbewzqDW4NaK_omSy2l_ZmX1K-WQ0
  verified: true
Drive mutation: none
```

Controlled live `/files` metadata upsert completed:

```text
script:
  scripts/live_metadata_upsert.py
files:
  1xOOLBOLz-tpaz6w5lWORFNtMyWPQO86v / 2026-05-27.md / text/markdown
  1C72TfkF6ReGS9wTbewzqDW4NaK_omSy2l_ZmX1K-WQ0 / AI_Bridge_Log_Spreadsheet / application/vnd.google-apps.spreadsheet
metadata_status: authoritative_loaded
source_registry_id: manual_live_probe
source_status: needs_human_review
index_eligible: false
human_block: false
verified: true
Drive mutation: none
```

Metadata-loader safe source quality defaults deployed:

```text
revision: capital-metadata-loader-00015-f6n
image: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/metadata-loader:source-quality-defaults-20260527
WRITE_ENABLED: false
DRIVE_REFETCH_ENABLED: false
PUBLISH_POLICY_JOBS: false
WORKER_VERSION: metadata-loader-source-quality-defaults
```

Metadata-loader preservation fix deployed:

```text
service: capital-metadata-loader
revision: capital-metadata-loader-00016-ttk
image: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/metadata-loader:preserve-source-quality-20260527
digest: sha256:0d237165e2cc9439be1cab1823faab812bdf9aa5a32f469a032d5025868b1e41
WRITE_ENABLED: false
DRIVE_REFETCH_ENABLED: false
PUBLISH_POLICY_JOBS: false
WORKER_VERSION: metadata-loader-preserve-source-quality
startup_probe: passed
```

Preservation rule:

```text
metadata refresh must preserve existing source_status, index_eligible and human_block.
Drive rescans must not erase human approvals or blocks in /files.
```

Drive scanner/reconciler local prototype completed:

```text
services/drive-scanner/src/drive_scanner/scanner.py
services/drive-scanner/tests/test_scanner.py
scripts/drive_scan_reconcile.py
```

Scanner contract:

```text
reads Drive metadata only
does not read file content
does not call AI
does not mutate Drive
turns Drive inventory into normalized events, then metadata-loader /files upserts
```

Controlled Drive scan dry-run:

```text
command: python scripts/drive_scan_reconcile.py --root-folder-id 1No6LMuCpH2T2jmGL7hnFlMto-0gnnHpq --max-files 10
write_enabled: false
folders_seen: 3
files: 10
truncated: true
would_write: 10
Drive mutation: none
```

Controlled Drive scan Firestore write:

```text
command: python scripts/drive_scan_reconcile.py --root-folder-id 1No6LMuCpH2T2jmGL7hnFlMto-0gnnHpq --max-files 10 --write
write_enabled: true
written_files: 10
metadata_status: authoritative_loaded
Drive mutation: none
```

Verified `/files` state after controlled scan:

```text
total_files: 11
needs_human_review/index_eligible_false: 9
active/index_eligible_true preserved: 1
legacy missing source-quality fields: 1
```

Verified tests:

```text
python -m unittest services/drive-scanner/tests/test_scanner.py services/metadata-loader/tests/test_firestore_writer.py -v
5 tests OK

full explicit service suite including drive-scanner
70 tests OK
```

Review queue handling completed:

```text
REVIEW_QUEUE_ENABLED=false by default
When WRITE_ENABLED=true and REVIEW_QUEUE_ENABLED=true:
  content-extractor writes /extracted_text/{file_id}
  then writes review-required extracted results to /review_queue/{review_id}
```

Review queue live verification:

```text
temporary revision: capital-content-extractor-00005-pzr
temporary WRITE_ENABLED: true
temporary DOCS_READ_ENABLED: true
temporary REVIEW_QUEUE_ENABLED: true
input_topic: capital.jobs.extraction
input_message_id: 19645214013174165
Cloud Run status: 200
review document: /review_queue/review_bc5cc34df88fd73116047fca
reason: empty_text
status: open
file_id: 1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM
verified: true
```

Review queue markdown projection completed:

```text
script: scripts/export_review_queue.py
output: docs/review/AI_REVIEW_QUEUE.md
source_of_truth: Firestore /review_queue
status: verified
open_items: 1
current_open_review_id: review_bc5cc34df88fd73116047fca
current_reason: empty_text
```

Admin web Next.js scaffold added:

```text
app: apps/admin-web
route: http://127.0.0.1:3000/review
api: /api/review-items
api: /api/review-items/{reviewId}/action
api: /api/review-items/{reviewId}/actions
api: /api/cleanup-items
api: /api/cleanup-items/{cleanupId}/action
data_source: Firestore REST via Next server routes
collections: /review_queue, /review_actions, /cleanup_queue, /cleanup_actions
browser_secret_boundary: no server credentials in browser bundle
auth: Firebase Auth Google sign-in, ADMIN_ALLOWED_EMAILS allowlist
production_url: https://capital-index-2026.web.app/review
cloud_run_service: capital-admin-web-run
current_image: europe-west4-docker.pkg.dev/capital-index-2026/firebaseapphosting-images/capital-admin-web-run:cleanup-queue-20260527
current_revision: capital-admin-web-run-00008-qtr
verified: typecheck, build, Cloud Build, Cloud Run deploy, /review 200, unauthenticated review/cleanup APIs return 401
```

---

## 9. Drive Governance decision

Drive Governance is now an explicit architecture requirement before broad AI analysis and graph extraction.

Documents added/updated:

```text
docs/adr/0003-drive-governance-before-ai.md
docs/runbooks/DRIVE_GOVERNANCE.md
docs/ARCHITECTURE.md
docs/ROADMAP.md
```

Core rule:

```text
Google Drive is not treated as clean source of truth by default.
Every AI-eligible file needs source_status and index_eligible.
Only source_status=active and index_eligible=true may enter entity extraction, embeddings, graph, or AI context.
Duplicate/stale/empty/archive/unknown files must not be used as independent evidence.
Cleanup recommendations require Policy Engine + human approval before Drive mutation.
Hard delete remains forbidden in automated flow.
```

Planned collections:

```text
/cleanup_queue
/cleanup_actions
/file_duplicates
```

Schemas:

```text
services/drive-governance/schemas/cleanup_queue.schema.json
services/drive-governance/schemas/cleanup_action.schema.json
services/drive-governance/schemas/file_duplicate.schema.json
```

MVP fixtures:

```text
tests/fixtures/drive-governance/file_inventory_governance_mvp.json
tests/fixtures/drive-governance/expected_cleanup_queue_governance_mvp.json
tests/fixtures/drive-governance/expected_file_duplicates_governance_mvp.json
```

Next implementation step:

```text
Drive Governance MVP local prototype is present:
services/drive-governance/src/drive_governance/governance.py
services/drive-governance/src/evaluate_governance.py
services/drive-governance/tests/test_governance.py

Covered detections:
empty candidate, duplicate-name/hash candidate, stale/version candidate, unknown-project candidate.

Verified:
python -m unittest services/drive-governance/tests/test_governance.py -v
python -m unittest services/event-ingestor/tests/test_normalize_drive_changes.py services/metadata-loader/tests/test_load_drive_metadata.py services/policy-engine-worker/tests/test_apply_policy.py services/content-extractor/tests/test_docs_reader.py services/drive-governance/tests/test_governance.py -v

Cleanup Queue admin UI completed:
apps/admin-web/app/review/cleanup-queue-panel.tsx
apps/admin-web/app/api/cleanup-items/route.ts
apps/admin-web/app/api/cleanup-items/[cleanupId]/action/route.ts
apps/admin-web/lib/cleanupQueue/

Cleanup UI behavior:
reads /cleanup_queue
writes /cleanup_actions
marks recommendations resolved
does not mutate Drive

Verified admin-web:
pnpm --filter @capital-index/admin-web typecheck
pnpm --filter @capital-index/admin-web build
Cloud Build image tag: cleanup-queue-20260527
Cloud Run revision: capital-admin-web-run-00008-qtr
https://capital-index-2026.web.app/review -> 200
/api/cleanup-items without auth -> 401

Source Files admin approval UI completed:
apps/admin-web/app/review/source-files-panel.tsx
apps/admin-web/app/api/files/route.ts
apps/admin-web/app/api/files/[fileId]/source-quality/route.ts
apps/admin-web/lib/sourceFiles/

Source Files behavior:
reads /files
writes /source_quality_actions
can set source_status active / needs_human_review / do_not_index
can set index_eligible and human_block
does not mutate Drive

Verified admin-web current deployment:
pnpm --filter @capital-index/admin-web typecheck
pnpm --filter @capital-index/admin-web build
Cloud Build image tag: source-files-20260527
Cloud Run revision: capital-admin-web-run-00009-2dc
https://capital-index-2026.web.app/review -> 200
/api/files without auth -> 401

Knowledge admin UI completed:
apps/admin-web/app/review/knowledge-panel.tsx
apps/admin-web/app/api/knowledge-items/route.ts
apps/admin-web/lib/knowledge/

Knowledge UI behavior:
reads /extracted_text
joins /entity_extractions by file_id
joins /files source quality fields
shows content preview, entity count, relationship count, entities and relationships
does not mutate Drive
does not call AI from the browser

Approved-source batch extraction script completed:
script: scripts/extract_approved_content.py
input: /files where source_status=active and index_eligible=true
output: /extracted_text when --write is used
supported: Google Docs, Google Sheets, Markdown/plain text
dry-run verified: eligible_files=1, skipped_existing=1, candidates=0

Rules-based source auto-classifier completed:
services/drive-governance/src/drive_governance/source_classifier.py
services/drive-governance/tests/test_source_classifier.py
script: scripts/apply_source_classification.py

Classifier rules:
preserve human decisions
Google Docs, Google Sheets and Markdown/plain text -> active/index_eligible=true when not temporary/archive/copy
technical, json, scripts, binaries -> do_not_index/index_eligible=false/human_block=true
archive/copy names -> candidate cleanup statuses
Drive mutation: none

Controlled source auto-classification:
command: python scripts/apply_source_classification.py --limit 250 --write
input_files: 250
active: 68
do_not_index: 180
needs_human_review: 2
preserved: 1
updated: 247
audit collection: /source_quality_actions

Controlled approved-source content extraction:
command: python scripts/extract_approved_content.py --limit 10 --write
eligible_files: 10
extracted_text_written: 10
review_required: 0
examples:
  Generate table of contents.md -> 357 chars
  CODEBASE_ANALYSIS_AGENT.md -> 619 chars
  critical-infrastructure.md -> 3925 chars
  AI_TODAY_CONTEXT -> 1041 chars

Controlled entity extraction after auto-classification:
command: python scripts/live_entity_extraction_probe.py --provider gemini --secret capital-gemini-api-key --model gemini-2.5-flash --limit 5 --write
input_files: 5
written_entity_extractions: 5
extracted: 1
needs_review: 4
successful file: AI_TODAY_CONTEXT_2026-05-23_2026-05-23_09-55-23
successful entities: 9
successful relationships: 6
notes: two Gemini calls timed out at 30s, needs retry/backoff before broad production batch.

Entity extraction batch/retry script completed:
script: scripts/entity_extraction_batch_retry.py
behavior:
  reads /extracted_text
  skips files with successful /entity_extractions status=extracted
  skips older failed entity extractions by default
  retries provider calls with configurable timeout/retries
  use --retry-failed to explicitly retry previous failed/needs_review files
  writes /entity_extractions only with --write
controlled dry-run:
  command: python scripts/entity_extraction_batch_retry.py --limit 3 --timeout 60 --retries 2
  input_extracted_text: 3
  extracted: 0
  needs_review: 3
controlled write:
  command: python scripts/entity_extraction_batch_retry.py --limit 5 --timeout 90 --retries 2 --write
  input_extracted_text: 5
  written_entity_extractions: 5
  extracted: 3
  needs_review: 2
  successful files:
    COPILOT_INSTRUCTIONS.md -> 13 entities / 8 relationships
    08_Source_Derived_Examples.md -> 37 entities / 32 relationships
    CLAUDE.md -> 18 entities / 17 relationships
  notes: two files still timed out at 90s and were written as needs_review for later retry.

Admin-web Knowledge deployment:
image: europe-west4-docker.pkg.dev/capital-index-2026/firebaseapphosting-images/capital-admin-web-run:knowledge-20260528
revision: capital-admin-web-run-00010-tcp
https://capital-index-2026.web.app/review -> 200
/api/knowledge-items without auth -> 401
Firestore currently has extracted_text=3 and entity_extractions=1

Admin progress dashboard completed:
apps/admin-web/app/review/progress-dashboard.tsx
apps/admin-web/app/api/progress-summary/route.ts
dashboard metrics:
  scanned files
  active
  do_not_index
  needs_human_review
  extracted_text
  entity_extractions
  understood/extracted
  needs_entity_review
  open cleanup recommendations
deployment:
  image: europe-west4-docker.pkg.dev/capital-index-2026/firebaseapphosting-images/capital-admin-web-run:progress-dashboard-20260528
  revision: capital-admin-web-run-00011-h8v
  typecheck: OK
  build: OK
  Cloud Run status: Ready

Next step:
promote source approval from per-file action to folder/rule-based auto-classification, then run content extraction for approved batches.
Do not implement Drive mutation or deletion yet.
```

Entity-extractor Drive Governance gate completed:

```text
services/entity-extractor/src/entity_extractor/source_guard.py
services/entity-extractor/src/entity_extractor/extraction.py
services/entity-extractor/src/entity_extractor/worker.py
services/entity-extractor/src/entity_extractor/inventory.py
services/entity-extractor/src/entity_extractor/firestore_writer.py
services/entity-extractor/src/app.py
services/entity-extractor/schemas/entity_extraction_candidate.schema.json
services/entity-extractor/schemas/extracted_entities.schema.json
services/entity-extractor/tests/test_source_guard.py
services/entity-extractor/tests/test_extraction.py
services/entity-extractor/tests/test_worker.py
services/entity-extractor/tests/test_firestore_writer.py
services/entity-extractor/tests/test_inventory.py
services/entity-extractor/tests/test_app.py
services/entity-extractor/tests/test_schema_contracts.py
tests/fixtures/entity-extractor/extracted_text_entity_gate_mvp.json
tests/fixtures/entity-extractor/file_records_entity_gate_mvp.json
tests/fixtures/entity-extractor/ai_response_entity_extraction_mvp.json
```

Gate rule:

```text
source_status = active
index_eligible = true
human_block = false
```

Blocked output:

```text
next_action: blocked
gate_reason: blocked_by_drive_governance
```

Verified:

```text
python -m unittest services/entity-extractor/tests/test_source_guard.py services/entity-extractor/tests/test_extraction.py services/entity-extractor/tests/test_worker.py services/entity-extractor/tests/test_firestore_writer.py services/entity-extractor/tests/test_inventory.py services/entity-extractor/tests/test_app.py services/entity-extractor/tests/test_schema_contracts.py -v
22 entity-extractor tests OK

python -m unittest services/event-ingestor/tests/test_normalize_drive_changes.py services/metadata-loader/tests/test_load_drive_metadata.py services/policy-engine-worker/tests/test_apply_policy.py services/content-extractor/tests/test_docs_reader.py services/content-extractor/tests/test_multiformat_extraction.py services/drive-governance/tests/test_governance.py services/drive-governance/tests/test_schema_contracts.py services/drive-governance/tests/test_firestore_writer.py services/drive-governance/tests/test_inventory.py services/drive-governance/tests/test_app.py services/entity-extractor/tests/test_source_guard.py services/entity-extractor/tests/test_extraction.py services/entity-extractor/tests/test_worker.py services/entity-extractor/tests/test_firestore_writer.py services/entity-extractor/tests/test_inventory.py services/entity-extractor/tests/test_app.py services/entity-extractor/tests/test_schema_contracts.py -v
58 tests OK
```

Entity-extractor AI extraction contract completed:

```text
provider-neutral prompt builder
AI JSON response normalizer
blocked candidates never use AI response
allowed candidates without AI response become needs_review
relationships require confidence >= 0.75
output collection target: /entity_extractions
live provider call: not implemented yet
```

Entity-extractor OpenAI adapter completed:

```text
services/entity-extractor/src/entity_extractor/ai_provider.py
services/entity-extractor/src/entity_extractor/secret_manager.py
services/entity-extractor/tests/test_ai_provider.py
provider: OpenAI Responses API
structured output: JSON Schema
secret name: capital-openai-api-key
secret state: created, no secret version added by Codex
secret access: capital-entity-extractor@capital-index-2026.iam.gserviceaccount.com has roles/secretmanager.secretAccessor on this secret only
AI_PROVIDER_ENABLED: false
OPENAI_MODEL_ID: gpt-5-mini
```

Entity-extractor Gemini adapter completed and live-tested:

```text
provider: Gemini generateContent API
model: gemini-2.5-flash
secret name: capital-gemini-api-key
secret state: version 1 added
secret access: capital-entity-extractor@capital-index-2026.iam.gserviceaccount.com has roles/secretmanager.secretAccessor on this secret
note: first user-provided key was a Google/Gemini key in capital-openai-api-key; it was copied to capital-gemini-api-key without printing the value
controlled dry-run:
  script: scripts/live_entity_extraction_probe.py
  provider: gemini
  write_enabled: false
  input_files: 1
  file: 2026-05-27.md
  extracted: 1
  entities: 7
  relationships: 7
  issues: []
controlled write:
  collection: /entity_extractions
  document: entity_extraction_453f8a24b2af348fba42f04c
  file_id: 1xOOLBOLz-tpaz6w5lWORFNtMyWPQO86v
  status: extracted
  entities: 7
  relationships: 7
```

Entity-extractor Cloud Run worker deployed:

```text
service: capital-entity-extractor
region: europe-west1
image: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/entity-extractor:gemini-provider-20260527
revision: capital-entity-extractor-00003-4vg
service_account: capital-entity-extractor@capital-index-2026.iam.gserviceaccount.com
endpoint: GET /healthz
endpoint: POST /extract-entities
WRITE_ENABLED: false
REQUEST_WRITE_ENABLED: false
AI_PROVIDER_ENABLED: false
AI_PROVIDER: gemini
GEMINI_API_KEY_SECRET_NAME: capital-gemini-api-key
GEMINI_MODEL_ID: gemini-2.5-flash
OPENAI_API_KEY_SECRET_NAME: capital-openai-api-key
EXTRACTION_LIMIT: 100
startup_probe: passed
Cloud Run status: Ready
```

Drive-governance Cloud Run worker deployed:

```text
service: capital-drive-governance
region: europe-west1
image: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/drive-governance:scheduled-20260527
revision: capital-drive-governance-00002-cxj
service_account: capital-drive-governance@capital-index-2026.iam.gserviceaccount.com
WRITE_ENABLED: false
REQUEST_WRITE_ENABLED: true
endpoint: POST /evaluate-governance
runtime_url: https://capital-drive-governance-4tc27qqqma-ew.a.run.app
```

Scheduled governance execution completed:

```text
job: capital-drive-governance-daily
location: europe-west1
schedule: 17 3 * * *
time_zone: Asia/Dubai
target: POST https://capital-drive-governance-4tc27qqqma-ew.a.run.app/evaluate-governance
body: {"write":true,"limit":250}
oidc_service_account: capital-drive-governance@capital-index-2026.iam.gserviceaccount.com
manual_run_verified_at: 2026-05-27T17:59:37Z
Cloud Run status: 200
```

Controlled governance Firestore write completed from local ADC:

```text
command: python services/drive-governance/src/write_governance_firestore.py --project capital-index-2026 --database "(default)" --limit 250 --write
input_files: 1
written_cleanup_queue: 1
written_file_duplicates: 0
cleanup_id: cleanup_000000000000000000000001
file_id: 1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM
reason: empty
source_status: candidate_empty
Drive mutation: none
```

Verified Firestore:

```text
/cleanup_queue open items: 1
cleanup_000000000000000000000001 empty candidate_empty
```

---

## 10. Do not repeat these mistakes

1. Do not create Firebase project with suffix like `capital-index-2026-29d10`.
   Correct project is `capital-index-2026`.

2. Do not create Firestore in `nam5`.
   Correct location is `eur3`.

3. Do not try to create service account JSON keys.
   Org policy blocks key creation and that is correct.

4. Do not keep fighting Workspace Events until exact auth/app requirements are verified.
   Use Drive Changes API fallback now.

5. Do not commit secrets or local tokens.

6. Do not invent Drive/Vault paths. Verify parent chain first.

---

## 11. User working style and constraint

The user wants execution, not commentary.

Important behavior rules for the next assistant:

```text
Do the task directly.
Do not expand scope unless required.
Do not claim completion if a tool failed.
Do not invent paths or state.
When giving commands, give only the next concrete command block.
When blocked, state blocker and the next decision.
```

The user strongly prefers:

```text
short operational answers
clear next action
no generic explanations
no repeated apologies
no artificial simplification of architecture
```

---

## 12. One-line continuation prompt

Continue CAPITAL INDEX from HANDOFF.md. Drive Changes fallback, event-ingestor, metadata-loader, policy-engine, content-extractor, drive-governance, entity-extractor, and capital-drive-scanner Cloud Run workers are deployed. Controlled /events, /files, /policy_decisions, /extracted_text, /review_queue, /cleanup_queue, and /entity_extractions Firestore writes are verified. Admin-web `/review` with Firebase Auth, Review Queue, Cleanup Queue, Source Files, Knowledge, and progress dashboard is verified. capital-drive-scanner now runs as the production Drive -> Firestore inventory path: Scheduler `capital-drive-scanner-daily` posts `{"write":true,"scan_mode":"all_drive","max_files":3000}`, Cloud Run revision `capital-drive-scanner-00004-j4r`, image `drive-scanner:all-drive-fast-20260529`, broad scan metadata-only, `DRIVE_REFETCH_ENABLED=false`, manual Scheduler run returned HTTP 200 in about 115s. Metadata refresh preserves existing `source_status`, `index_eligible`, and `human_block`. Drive Governance is required before broad AI/entity extraction: only `source_status=active`, `index_eligible=true`, `human_block=false` may enter content extraction, entity extraction, graph, embeddings, or AI context. AI may write proposal fields only; policy, review orchestrator, or human approval writes authoritative decisions. Workers remain guarded when idle: Drive mutation is forbidden, hard delete is forbidden, and restricted context publication requires approval. Next step: persist Drive scanner scan state/page tokens in Firestore, expose scanner coverage/progress in Admin Web, then run governance over expanded `/files` inventory before promoting approved files into content/entity extraction and context bundles.
