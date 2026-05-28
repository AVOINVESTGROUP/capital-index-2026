# Drive Governance Runbook

## Purpose

Drive Governance protects CAPITAL INDEX from using noisy, outdated, duplicated, empty, or irrelevant
Drive files as AI evidence.

This layer exists because file clutter directly lowers AI quality.

## Rule

```text
Do not analyze everything just because it exists in Drive.
First decide whether the file is a valid source.
```

AI analysis, embeddings, project summaries, graph extraction, and context publishing may only use a
file when:

```text
source_status = active
index_eligible = true
policy_allowed = true
human_block = false
```

## Source Statuses

```text
active
candidate_duplicate
candidate_stale
candidate_empty
candidate_archive
do_not_index
needs_human_review
```

## Cleanup Queue

Collection:

```text
/cleanup_queue/{cleanup_id}
```

Schema:

```text
services/drive-governance/schemas/cleanup_queue.schema.json
```

A cleanup queue item is a recommendation, not an action.

Example reasons:

```text
duplicate
near_duplicate
stale
empty
orphaned
version_superseded
unknown_project
temporary_name
```

Example recommended actions:

```text
keep_active
mark_duplicate
archive
move_to_review
do_not_index
needs_review
```

## Operator Decisions

The admin UI must let an operator decide:

```text
Keep active
Mark duplicate
Archive candidate
Move to review folder
Do not index
Ignore recommendation
Open in Drive
```

Every decision must write:

```text
/cleanup_actions/{action_id}
```

Schema:

```text
services/drive-governance/schemas/cleanup_action.schema.json
```

Required audit fields:

```text
action_id
cleanup_id
file_id
actor_id
actor_type
action
previous_source_status
new_source_status
drive_mutation
drive_mutation_allowed
note
created_at
```

## Detection Signals

MVP signals:

```text
empty text result
zero or very low char_count
same normalized file name
same mime type and similar modified_time
same content hash when available
near-identical extracted text when available
old modified_time relative to folder/project state
file name contains copy, old, final final, draft, backup, v1, v2
unknown project_id
missing source_registry_id
trashed = true
```

Duplicate cluster schema:

```text
services/drive-governance/schemas/file_duplicate.schema.json
```

Later signals:

```text
Drive Activity API last viewed/opened
Drive Labels
owner and permission drift
project status
contract signed-state detection
semantic similarity
manual override history
```

## Safe Actions

Allowed before human approval:

```text
write recommendation
write source_status candidate
write index_eligible = false for obvious blocked states
show item in admin UI
exclude item from AI context
```

Allowed after human approval:

```text
mark active
mark duplicate
mark do_not_index
mark archive candidate
move to review folder
apply Drive label
archive by move
```

Forbidden in automated flow:

```text
hard delete
permanent trash cleanup
publishing restricted context
using stale/duplicate files as independent evidence
overriding manual human decision
```

## MVP Flow

```text
1. metadata-loader writes /files/{file_id}
2. drive-governance-worker reads /files and available extracted_text stats
3. worker assigns source_status and index_eligible
4. worker creates /cleanup_queue item when action is uncertain or destructive
5. admin UI shows cleanup recommendation
6. human decides
7. cleanup action is written to /cleanup_actions
8. only active/index_eligible files continue to AI extraction and graph
```

## First MVP Scope

Implement only recommendation generation:

```text
empty candidate
duplicate-name candidate
stale-name/version candidate
unknown-project candidate
```

Do not implement Drive mutation in MVP.

Do not implement deletion in MVP.

MVP fixtures:

```text
tests/fixtures/drive-governance/file_inventory_governance_mvp.json
tests/fixtures/drive-governance/expected_cleanup_queue_governance_mvp.json
tests/fixtures/drive-governance/expected_file_duplicates_governance_mvp.json
```

MVP local module:

```text
services/drive-governance/src/drive_governance/governance.py
services/drive-governance/src/evaluate_governance.py
services/drive-governance/tests/test_governance.py
```

Verified command:

```text
python -m unittest services/drive-governance/tests/test_governance.py -v
```

Contract test:

```text
services/drive-governance/tests/test_schema_contracts.py
```

Firestore write boundary:

```text
services/drive-governance/src/drive_governance/firestore_writer.py
services/drive-governance/tests/test_firestore_writer.py
WRITE_ENABLED=false by default
```

Cloud Run worker:

```text
service: capital-drive-governance
region: europe-west1
image: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/drive-governance:scheduled-20260527
revision: capital-drive-governance-00002-cxj
runtime_service_account: capital-drive-governance@capital-index-2026.iam.gserviceaccount.com
WRITE_ENABLED: false
REQUEST_WRITE_ENABLED: true
endpoint: POST /evaluate-governance
```

Request write gate:

```text
WRITE_ENABLED=false keeps empty/manual POST requests as dry-run.
REQUEST_WRITE_ENABLED=true allows scheduled POST {"write": true, "limit": 250}.
Drive mutation is still none.
```

Scheduled execution:

```text
job: capital-drive-governance-daily
location: europe-west1
schedule: 17 3 * * *
time_zone: Asia/Dubai
target: POST /evaluate-governance
body: {"write":true,"limit":250}
oidc_service_account: capital-drive-governance@capital-index-2026.iam.gserviceaccount.com
```

Scheduler verification:

```text
manual_run: gcloud scheduler jobs run capital-drive-governance-daily --project capital-index-2026 --location europe-west1
last_attempt: 2026-05-27T17:59:37Z
Cloud Run status: 200
Firestore document: /cleanup_queue/cleanup_000000000000000000000001
verified: true
```

Manual Firestore evaluation:

```text
python services/drive-governance/src/write_governance_firestore.py --project capital-index-2026 --database "(default)" --limit 250
```

Controlled Firestore write:

```text
python services/drive-governance/src/write_governance_firestore.py --project capital-index-2026 --database "(default)" --limit 250 --write
```

Current verified production result:

```text
input_files: 1
cleanup_queue_written: 1
file_duplicates_written: 0
open_cleanup_item: cleanup_000000000000000000000001
reason: empty
source_status: candidate_empty
Drive mutation: none
```

## Drive Scan Reconciliation

Drive scan reconciliation is the controlled way to turn a real Drive folder tree into `/files`
inventory records.

It reads Drive metadata only:

```text
file id
name
mime type
parents
trashed
created/modified time
web link
size when available
```

It does not:

```text
read file content
call AI
move/archive/delete Drive files
mark files active automatically
```

Local scanner module:

```text
services/drive-scanner/src/drive_scanner/scanner.py
services/drive-scanner/tests/test_scanner.py
scripts/drive_scan_reconcile.py
```

Metadata preservation rule:

```text
metadata-loader must preserve existing source_status, index_eligible and human_block.
Drive rescans must not erase human approvals or blocks.
```

Verified tests:

```text
python -m unittest services/drive-scanner/tests/test_scanner.py services/metadata-loader/tests/test_firestore_writer.py -v
python -m unittest services/event-ingestor/tests/test_normalize_drive_changes.py services/event-ingestor/tests/test_extraction_plan.py services/metadata-loader/tests/test_load_drive_metadata.py services/metadata-loader/tests/test_drive_refetch.py services/metadata-loader/tests/test_firestore_writer.py services/metadata-loader/tests/test_job_publisher.py services/metadata-loader/tests/test_pubsub.py services/policy-engine-worker/tests/test_apply_policy.py services/policy-engine-worker/tests/test_firestore_writer.py services/policy-engine-worker/tests/test_pubsub.py services/content-extractor/tests/test_docs_reader.py services/content-extractor/tests/test_review_queue.py services/content-extractor/tests/test_multiformat_extraction.py services/drive-governance/tests/test_governance.py services/drive-governance/tests/test_schema_contracts.py services/drive-governance/tests/test_firestore_writer.py services/drive-governance/tests/test_inventory.py services/drive-governance/tests/test_app.py services/entity-extractor/tests/test_source_guard.py services/entity-extractor/tests/test_extraction.py services/entity-extractor/tests/test_worker.py services/entity-extractor/tests/test_firestore_writer.py services/entity-extractor/tests/test_inventory.py services/entity-extractor/tests/test_app.py services/entity-extractor/tests/test_schema_contracts.py services/entity-extractor/tests/test_ai_provider.py -v
```

Controlled dry run:

```text
python scripts/drive_scan_reconcile.py --root-folder-id 1No6LMuCpH2T2jmGL7hnFlMto-0gnnHpq --max-files 10
write_enabled: false
folders_seen: 3
files: 10
truncated: true
Drive mutation: none
```

Controlled Firestore write:

```text
python scripts/drive_scan_reconcile.py --root-folder-id 1No6LMuCpH2T2jmGL7hnFlMto-0gnnHpq --max-files 10 --write
write_enabled: true
written: 10
metadata_status: authoritative_loaded
Drive mutation: none
```

Current verified `/files` state after controlled scan:

```text
total_files: 11
active/index_eligible preserved: 1
new needs_human_review/index_eligible_false: 9
legacy missing source-quality fields: 1
```

Current metadata-loader production revision with preservation fix:

```text
service: capital-metadata-loader
revision: capital-metadata-loader-00016-ttk
image: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/metadata-loader:preserve-source-quality-20260527
WRITE_ENABLED: false
DRIVE_REFETCH_ENABLED: false
PUBLISH_POLICY_JOBS: false
startup_probe: passed
```

## Admin UI

Cleanup Queue is available in the admin web app:

```text
https://capital-index-2026.web.app/review
```

The screen has three queues:

```text
Review Queue
Cleanup Queue
Source Files
```

Cleanup Queue reads:

```text
GET /api/cleanup-items?status=open&limit=100
```

Cleanup decisions write:

```text
POST /api/cleanup-items/{cleanup_id}/action
```

Supported actions:

```text
keep_active
mark_duplicate
archive
move_to_review
do_not_index
ignore
```

The admin action records `/cleanup_actions/{action_id}` and marks the recommendation resolved.
It does not mutate Drive files. `drive_mutation` remains `none` in the MVP.

Source Files reads:

```text
GET /api/files?status=needs_human_review&limit=100
```

Source quality decisions write:

```text
POST /api/files/{file_id}/source-quality
```

Supported actions:

```text
activate
needs_review
do_not_index
```

Effects:

```text
activate -> source_status=active, index_eligible=true, human_block=false
needs_review -> source_status=needs_human_review, index_eligible=false, human_block=false
do_not_index -> source_status=do_not_index, index_eligible=false, human_block=true
```

Every source quality decision writes:

```text
/source_quality_actions/{action_id}
```

Source quality actions do not mutate Drive files. `drive_mutation` remains `none`.

Verified deployment:

```text
image: europe-west4-docker.pkg.dev/capital-index-2026/firebaseapphosting-images/capital-admin-web-run:source-files-20260527
revision: capital-admin-web-run-00009-2dc
https://capital-index-2026.web.app/review -> 200
/api/files without auth -> 401
```

Verified combined command:

```text
python -m unittest services/event-ingestor/tests/test_normalize_drive_changes.py services/metadata-loader/tests/test_load_drive_metadata.py services/policy-engine-worker/tests/test_apply_policy.py services/content-extractor/tests/test_docs_reader.py services/drive-governance/tests/test_governance.py services/drive-governance/tests/test_schema_contracts.py services/drive-governance/tests/test_firestore_writer.py -v
```

## Entity Extraction Gate

Entity extraction must not run directly on every `/extracted_text` document.

Required file state:

```text
source_status = active
index_eligible = true
human_block = false
```

Safe `/files` defaults written by metadata-loader:

```text
source_status = needs_human_review
index_eligible = false
human_block = false
```

This means newly observed files are blocked from entity extraction until a later approval path marks them active.

Implemented contract:

```text
services/entity-extractor/src/entity_extractor/source_guard.py
services/entity-extractor/schemas/entity_extraction_candidate.schema.json
services/entity-extractor/tests/test_source_guard.py
services/entity-extractor/tests/test_schema_contracts.py
```

Blocked files emit:

```text
next_action: blocked
gate_reason: blocked_by_drive_governance
```

Allowed files emit:

```text
next_action: extract_entities
gate_reason: allowed
```

Verified command:

```text
python -m unittest services/entity-extractor/tests/test_source_guard.py services/entity-extractor/tests/test_schema_contracts.py -v
```

## Practical Impact

Without Drive Governance:

```text
AI may treat old and duplicate files as current truth.
```

With Drive Governance:

```text
AI sees fewer files, but higher-quality evidence.
Project summaries become more accurate.
Confidence scores become less inflated by duplicated evidence.
Human operators control destructive or sensitive cleanup.
```

## Content Coverage

Content extraction must cover more than Google Docs.

Current content-extractor code supports:

```text
Google Docs: Docs API
Google Sheets: Sheets API
Markdown/plain text: Drive API download
```

Runtime read flags:

```text
DOCS_READ_ENABLED=false
SHEETS_READ_ENABLED=false
DRIVE_READ_ENABLED=false
```

Verified tests:

```text
python -m unittest services/content-extractor/tests/test_docs_reader.py services/content-extractor/tests/test_multiformat_extraction.py -v
```

Controlled live extraction verified:

```text
script: scripts/live_multiformat_extraction_probe.py
markdown_file_id: 1xOOLBOLz-tpaz6w5lWORFNtMyWPQO86v
markdown_title: 2026-05-27.md
markdown_char_count: 236
sheet_file_id: 1C72TfkF6ReGS9wTbewzqDW4NaK_omSy2l_ZmX1K-WQ0
sheet_title: AI_Bridge_Log_Spreadsheet
sheet_char_count: 209330
Firestore collection: /extracted_text
written: true
Drive mutation: none
```

Controlled live `/files` metadata upsert verified:

```text
script: scripts/live_metadata_upsert.py
markdown_file_id: 1xOOLBOLz-tpaz6w5lWORFNtMyWPQO86v
sheet_file_id: 1C72TfkF6ReGS9wTbewzqDW4NaK_omSy2l_ZmX1K-WQ0
metadata_status: authoritative_loaded
source_status: needs_human_review
index_eligible: false
human_block: false
metadata_loader_revision: capital-metadata-loader-00015-f6n
Drive mutation: none
```
