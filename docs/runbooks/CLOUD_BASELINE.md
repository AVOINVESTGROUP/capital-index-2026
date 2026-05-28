# CLOUD_BASELINE.md - CAPITAL INDEX 2026

## Status

Cloud baseline is ready for the next worker.
The event-ingestor -> metadata-loader Pub/Sub chain is verified end to end.

## Project

```text
project_id: capital-index-2026
project_number: 745677061768
billing_enabled: true
region: europe-west1
artifact_repository: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers
```

## APIs enabled after billing

```text
run.googleapis.com
cloudbuild.googleapis.com
artifactregistry.googleapis.com
containerregistry.googleapis.com
```

## Artifact Registry

```text
repository: capital-workers
location: europe-west1
format: DOCKER
uri: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers
```

Cloud Build runtime IAM:

```text
745677061768-compute@developer.gserviceaccount.com:
  roles/storage.objectViewer on gs://capital-index-2026_cloudbuild
  roles/artifactregistry.writer on capital-workers
  roles/logging.logWriter on project
```

## Worker service accounts

```text
capital-event-ingestor@capital-index-2026.iam.gserviceaccount.com
capital-metadata-loader@capital-index-2026.iam.gserviceaccount.com
capital-policy-engine@capital-index-2026.iam.gserviceaccount.com
capital-content-extractor@capital-index-2026.iam.gserviceaccount.com
```

Baseline IAM:

```text
roles/datastore.user on project for the four worker service accounts
roles/iam.serviceAccountTokenCreator on capital-workspace-reader for:
  capital-event-ingestor
  capital-metadata-loader
  capital-content-extractor
```

`capital-policy-engine` does not need Workspace DWD signing.

Pub/Sub IAM:

```text
capital-event-ingestor:
  subscriber on capital.events.drive.ingestor
  publisher on capital.jobs.metadata
  publisher on capital.audit

capital-metadata-loader:
  subscriber on capital.jobs.metadata.worker
  publisher on capital.jobs.policy
  publisher on capital.audit

capital-policy-engine:
  subscriber on capital.jobs.policy.worker
  publisher on capital.jobs.extraction
  publisher on capital.audit

capital-content-extractor:
  subscriber on capital.jobs.extraction.worker
  publisher on capital.audit
```

## Pub/Sub topics

```text
capital.events.drive
capital.jobs.metadata
capital.jobs.policy
capital.jobs.extraction
capital.audit
capital.dlq
capital-events-drive-test
```

## Pub/Sub subscriptions

```text
capital.events.drive.ingestor -> capital.events.drive
capital.events.drive.ingestor.push -> capital.events.drive
capital.jobs.metadata.worker -> capital.jobs.metadata
capital.jobs.metadata.worker.push -> capital.jobs.metadata
capital.jobs.policy.worker -> capital.jobs.policy
capital.jobs.policy.worker.push -> capital.jobs.policy
capital.jobs.extraction.worker -> capital.jobs.extraction
capital.jobs.extraction.worker.push -> capital.jobs.extraction
capital-events-drive-test-sub -> capital-events-drive-test
```

Worker subscriptions were created with:

```text
dead_letter_topic: capital.dlq
max_delivery_attempts: 5
```

Push subscriptions:

```text
subscription: capital.events.drive.ingestor.push
topic: capital.events.drive
push_endpoint: https://capital-event-ingestor-745677061768.europe-west1.run.app/pubsub/drive-changes
oidc_service_account: capital-event-ingestor@capital-index-2026.iam.gserviceaccount.com
dead_letter_topic: capital.dlq
max_delivery_attempts: 5
status: verified

subscription: capital.jobs.metadata.worker.push
topic: capital.jobs.metadata
push_endpoint: https://capital-metadata-loader-745677061768.europe-west1.run.app/pubsub/metadata
oidc_service_account: capital-metadata-loader@capital-index-2026.iam.gserviceaccount.com
dead_letter_topic: capital.dlq
max_delivery_attempts: 5
status: verified

subscription: capital.jobs.policy.worker.push
topic: capital.jobs.policy
push_endpoint: https://capital-policy-engine-745677061768.europe-west1.run.app/pubsub/policy
oidc_service_account: capital-policy-engine@capital-index-2026.iam.gserviceaccount.com
dead_letter_topic: capital.dlq
max_delivery_attempts: 5
status: verified

subscription: capital.jobs.extraction.worker.push
topic: capital.jobs.extraction
push_endpoint: https://capital-content-extractor-745677061768.europe-west1.run.app/pubsub/extraction
oidc_service_account: capital-content-extractor@capital-index-2026.iam.gserviceaccount.com
dead_letter_topic: capital.dlq
max_delivery_attempts: 5
status: verified
```

## Firebase CLI status

`firebase deploy --only firestore:rules,firestore:indexes --project capital-index-2026`
completed successfully after Firebase CLI reauth.

```text
firestore.rules compiled successfully
firestore.indexes.json deployed successfully for (default)
rules released to cloud.firestore
```

## Next

```text
1. Add operator authentication and deploy admin-web.
2. Connect review actions to downstream review-orchestrator flow.
3. Start graph/entity extraction from accepted extracted_text.
```

## First Cloud Run worker

`capital-event-ingestor` was built and deployed as an authenticated Cloud Run service.
It has a Firestore write boundary, but writes are disabled by environment config.

```text
service: capital-event-ingestor
region: europe-west1
ingress: all, authenticated only
service_account: capital-event-ingestor@capital-index-2026.iam.gserviceaccount.com
image: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/event-ingestor:latest
revision: capital-event-ingestor-00016-zvk
WRITE_ENABLED: false
PUBLISH_METADATA_JOBS: false
METADATA_JOBS_TOPIC: capital.jobs.metadata
WORKER_VERSION: event-ingestor-e2e-verified
status: Ready
```

Endpoints:

```text
GET /healthz
POST /normalize-drive-changes
POST /pubsub/drive-changes
```

Write boundary:

```text
WRITE_ENABLED=false:
  returns dry-run write summary
  no Firestore client is created

WRITE_ENABLED=true:
  upserts normalized events to /events/{event_id}

PUBLISH_METADATA_JOBS=true:
  publishes the normalized batch to capital.jobs.metadata after /events write succeeds
```

Controlled Firestore write verification:

```text
temporary revision: capital-event-ingestor-00005-7lj
temporary ingress: all, authenticated only
temporary WRITE_ENABLED: true
test event_id: evt_888e52cfd457eb5c126b00bf
Firestore document: /events/evt_888e52cfd457eb5c126b00bf
write_source: event-ingestor
firestore_schema_version: capital.events.v1
result: verified
```

After the test, the service was returned to:

```text
ingress: internal
WRITE_ENABLED: false
revision: capital-event-ingestor-00006-22k
```

Pub/Sub push execution verification:

```text
subscription: capital.events.drive.ingestor.push
published_message_id: 19644170894832603
Cloud Run endpoint: POST /pubsub/drive-changes
Cloud Run status: 200
Firestore document: /events/evt_888e52cfd457eb5c126b00bf
raw_payload_ref: pubsub://message/19644170894832603#/folder_changes/0
result: verified
```

Final safe Cloud Run state after Pub/Sub verification:

```text
ingress: all, authenticated only
WRITE_ENABLED: false
WORKER_VERSION: event-ingestor-pubsub-verified
revision: capital-event-ingestor-00013-w5f
```

End-to-end event -> metadata verification:

```text
input_topic: capital.events.drive
input_message_id: 19644990894445117
event-ingestor endpoint: POST /pubsub/drive-changes
event-ingestor status: 200
event document: /events/evt_888e52cfd457eb5c126b00bf
event written_at: 2026-05-27T09:04:30+00:00
metadata-loader endpoint: POST /pubsub/metadata
metadata-loader status: 200
file document: /files/1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM
file updated_at: 2026-05-27T09:04:35+00:00
result: verified
```

Final safe Cloud Run state after end-to-end verification:

```text
ingress: all, authenticated only
WRITE_ENABLED: false
PUBLISH_METADATA_JOBS: false
WORKER_VERSION: event-ingestor-e2e-verified
revision: capital-event-ingestor-00016-zvk
```

## Second Cloud Run worker

`capital-metadata-loader` was built and deployed as an authenticated Cloud Run service.
It has a Firestore write boundary, and writes are disabled by environment config.

```text
service: capital-metadata-loader
region: europe-west1
ingress: all, authenticated only
service_account: capital-metadata-loader@capital-index-2026.iam.gserviceaccount.com
image: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/metadata-loader:latest
revision: capital-metadata-loader-00014-hm4
WRITE_ENABLED: false
DRIVE_REFETCH_ENABLED: false
DRIVE_SUBJECT_EMAIL: office@integrayachtsuae.com
PUBLISH_POLICY_JOBS: false
POLICY_JOBS_TOPIC: capital.jobs.policy
WORKER_VERSION: metadata-loader-policy-e2e-verified
status: Ready
```

Endpoints:

```text
GET /healthz
POST /load-drive-metadata
POST /pubsub/metadata
```

Write boundary:

```text
WRITE_ENABLED=false:
  returns dry-run write summary
  no Firestore client is created

WRITE_ENABLED=true:
  upserts file metadata to /files/{file_id}

DRIVE_REFETCH_ENABLED=true:
  fetches owners, head revision, capabilities and permissions summary from Drive API
  sets metadata_status=authoritative_loaded when successful

PUBLISH_POLICY_JOBS=true:
  publishes the metadata batch to capital.jobs.policy after /files write succeeds
```

Controlled Firestore write verification:

```text
temporary revision: capital-metadata-loader-00002-8dl
temporary WRITE_ENABLED: true
Firestore document: /files/1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM
write_source: metadata-loader
firestore_schema_version: capital.files.v1
result: verified
```

Pub/Sub push execution verification:

```text
subscription: capital.jobs.metadata.worker.push
published_message_id: 19644059606693559
Cloud Run endpoint: POST /pubsub/metadata
Cloud Run status: 200
Firestore document: /files/1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM
updated_at: 2026-05-27T08:49:14+00:00
result: verified
```

Final safe Cloud Run state after Pub/Sub verification:

```text
ingress: all, authenticated only
WRITE_ENABLED: false
WORKER_VERSION: metadata-loader-pubsub-verified
revision: capital-metadata-loader-00006-v7p
```

Final safe Cloud Run state after end-to-end verification:

```text
ingress: all, authenticated only
WRITE_ENABLED: false
WORKER_VERSION: metadata-loader-e2e-verified
revision: capital-metadata-loader-00008-6js
```

Drive API authoritative refetch verification:

```text
temporary revision: capital-metadata-loader-00010-5dz
temporary WRITE_ENABLED: true
temporary DRIVE_REFETCH_ENABLED: true
endpoint: POST /load-drive-metadata
Firestore document: /files/1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM
metadata_status: authoritative_loaded
authoritative_refetch_status: loaded
owner: office@integrayachtsuae.com
head_revision_id: 1
permissions_summary.total: 1
result: verified
```

Final safe Cloud Run state after Drive refetch verification:

```text
ingress: all, authenticated only
WRITE_ENABLED: false
DRIVE_REFETCH_ENABLED: false
WORKER_VERSION: metadata-loader-drive-refetch-verified
revision: capital-metadata-loader-00011-wkl
```

Metadata -> policy end-to-end verification:

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
result: verified
```

Final metadata-loader safe state after policy e2e verification:

```text
ingress: all, authenticated only
WRITE_ENABLED: false
DRIVE_REFETCH_ENABLED: false
PUBLISH_POLICY_JOBS: false
WORKER_VERSION: metadata-loader-policy-e2e-verified
revision: capital-metadata-loader-00014-hm4
```

## Third Cloud Run worker

`capital-policy-engine` was built and deployed as an authenticated Cloud Run service.
It has a Firestore write boundary, and writes are disabled by environment config.

```text
service: capital-policy-engine
region: europe-west1
ingress: all, authenticated only
service_account: capital-policy-engine@capital-index-2026.iam.gserviceaccount.com
image: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/policy-engine-worker:latest
revision: capital-policy-engine-00008-xh5
WRITE_ENABLED: false
PUBLISH_EXTRACTION_JOBS: false
EXTRACTION_JOBS_TOPIC: capital.jobs.extraction
WORKER_VERSION: policy-engine-extraction-e2e-verified
status: Ready
```

Endpoints:

```text
GET /healthz
POST /apply-policy
POST /pubsub/policy
```

Write boundary:

```text
WRITE_ENABLED=false:
  returns dry-run write summary
  no Firestore client is created

WRITE_ENABLED=true:
  upserts policy decisions to /policy_decisions/{decision_id}

PUBLISH_EXTRACTION_JOBS=true:
  publishes content extraction candidates to capital.jobs.extraction after /policy_decisions write succeeds
```

Pub/Sub push execution verification:

```text
subscription: capital.jobs.policy.worker.push
published_message_id: 19644335376522148
Cloud Run endpoint: POST /pubsub/policy
Cloud Run status: 200
Firestore document: /policy_decisions/policy_7f56e9fe6ddee8aff5f36794
result: verified
```

Final safe Cloud Run state after policy e2e verification:

```text
ingress: all, authenticated only
WRITE_ENABLED: false
PUBLISH_EXTRACTION_JOBS: false
WORKER_VERSION: policy-engine-extraction-e2e-verified
revision: capital-policy-engine-00008-xh5
```

Policy -> extraction end-to-end verification:

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
result: verified
```

## Fourth Cloud Run worker

`capital-content-extractor` was built and deployed as an authenticated Cloud Run service.
It has Firestore and Docs API read boundaries, and both are disabled by environment config.

```text
service: capital-content-extractor
region: europe-west1
ingress: all, authenticated only
service_account: capital-content-extractor@capital-index-2026.iam.gserviceaccount.com
image: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/content-extractor:latest
revision: capital-content-extractor-00006-sgx
WRITE_ENABLED: false
DOCS_READ_ENABLED: false
REVIEW_QUEUE_ENABLED: false
DOCS_SUBJECT_EMAIL: office@integrayachtsuae.com
WORKER_VERSION: content-extractor-review-queue-verified
status: Ready
```

Endpoints:

```text
GET /healthz
POST /extract-content
POST /pubsub/extraction
```

Boundaries:

```text
WRITE_ENABLED=false:
  returns dry-run write summary
  no Firestore client is created

DOCS_READ_ENABLED=false:
  does not call Docs API

WRITE_ENABLED=true and DOCS_READ_ENABLED=true:
  reads allowed Google Docs text and upserts /extracted_text/{file_id}

REVIEW_QUEUE_ENABLED=true:
  upserts review-required extraction results to /review_queue/{review_id}
```

Final safe Cloud Run state after extraction e2e verification:

```text
ingress: all, authenticated only
WRITE_ENABLED: false
DOCS_READ_ENABLED: false
WORKER_VERSION: content-extractor-e2e-verified
revision: capital-content-extractor-00003-dt2
```

Review queue verification:

```text
temporary revision: capital-content-extractor-00005-pzr
temporary WRITE_ENABLED: true
temporary DOCS_READ_ENABLED: true
temporary REVIEW_QUEUE_ENABLED: true
input_topic: capital.jobs.extraction
input_message_id: 19645214013174165
content-extractor endpoint: POST /pubsub/extraction
content-extractor status: 200
review document: /review_queue/review_bc5cc34df88fd73116047fca
reason: empty_text
status: open
file_id: 1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM
result: verified
```

Final safe Cloud Run state after review_queue verification:

```text
ingress: all, authenticated only
WRITE_ENABLED: false
DOCS_READ_ENABLED: false
REVIEW_QUEUE_ENABLED: false
WORKER_VERSION: content-extractor-review-queue-verified
revision: capital-content-extractor-00006-sgx
```

## Review queue projection

Firestore `/review_queue` is projected into a local operator markdown view:

```text
script: scripts/export_review_queue.py
output: docs/review/AI_REVIEW_QUEUE.md
source_of_truth: Firestore /review_queue
status: verified
```

Verified command:

```text
python scripts/export_review_queue.py --project capital-index-2026 --database "(default)" --status open --limit 100 --output docs/review/AI_REVIEW_QUEUE.md
```

Current live projection contains one open item:

```text
review_id: review_bc5cc34df88fd73116047fca
reason: empty_text
file_id: 1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM
title: drive-probe-test-001
```

## Admin web

The first Next.js operator console is available locally:

```text
app: apps/admin-web
route: http://127.0.0.1:3000/review
api: /api/review-items
api: /api/review-items/{reviewId}/action
source: Firestore /review_queue
audit_collection: /review_actions
```

Local verification:

```text
npm --workspace apps/admin-web run typecheck
npm --workspace apps/admin-web run build
npm audit --audit-level=moderate
GET /review -> 200
GET /api/review-items?status=open&limit=5 -> 1 live item
POST invalid action -> 400
```

Important:

```text
Do not use the action buttons to approve or close restricted work without human operator intent.
The browser does not receive server credentials.
Local dev uses gcloud ADC through the Next server route.
```

Production deployment:

```text
public URL: https://capital-index-2026.web.app/review
routing: Firebase Hosting rewrite -> Cloud Run
cloud run service: capital-admin-web-run
region: europe-west4
image: europe-west4-docker.pkg.dev/capital-index-2026/firebaseapphosting-images/capital-admin-web-run:review-audit-20260527
runtime service account: capital-admin-web@capital-index-2026.iam.gserviceaccount.com
source app: apps/admin-web
container config: apps/admin-web/Dockerfile
hosting config: firebase.json
```

Access control:

```text
browser auth: Firebase Auth Google sign-in
server auth: Firebase Admin ID token verification in Next API routes
allowed operators: ADMIN_ALLOWED_EMAILS
current allowlist: office@integrayachtsuae.com
public Firebase config: NEXT_PUBLIC_FIREBASE_* Cloud Run env vars
review page caching: /review is dynamic and Firebase Hosting sends no-store headers
Firebase Auth project config: initialized through Identity Toolkit initializeAuth
Google provider: must be enabled in Firebase Console unless OAuth client id/secret are managed separately
```

Live verification:

```text
GET https://capital-index-2026.web.app/review -> 200
GET https://capital-index-2026.web.app/api/firebase-config -> 200
GET https://capital-index-2026.web.app/api/review-items?status=open&limit=5 without bearer token -> 401
GET https://capital-index-2026.web.app/api/review-items/{reviewId}/actions without bearer token -> 401
GET https://capital-index-2026.web.app/api/review-items?status=open&limit=5 with allowed Firebase ID token -> 200
```

Note:

```text
Firebase App Hosting backend capital-admin-web exists, but direct App Hosting rollout is not the active production path.
The working path is Firebase Hosting + Cloud Run because App Hosting packaging dropped Next runtime dependencies for this npm/pnpm workspace shape.
```
