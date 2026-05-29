# Google Workspace Native Governance

Date: 2026-05-28

## Goal

Use Google-native tools where they reduce custom code:

- Cloud Run Drive Scanner writes the primary file inventory into Firestore `/files`.
- Google Drive Labels become the native file-level source quality layer.
- Admin Web is the operator control surface for inspection, correction and approval.
- Google Sheet `CAPITAL_INDEX_2026` remains a migration table and manual fallback, not
  the production database.
- Apps Script is allowed for migration, diagnostics and emergency manual sync only.

The system must not analyze the whole Drive as an untrusted dump.

## Production Order

```text
Drive files
  -> Cloud Run Drive Scanner upserts Firestore /files
  -> Drive Governance assigns safe source-quality defaults
  -> AI classifier writes proposals, summaries and confidence
  -> Admin Web lets the operator approve, correct, block or route to review
  -> Policy Engine decides whether AI may read content
  -> Content extraction and entity extraction run only for approved files
  -> Context Publisher builds AI context bundles and Obsidian projections
```

## Legacy Sheet Path

The Google Sheet and Apps Script path remains useful for:

- migration from the current `CAPITAL_INDEX_2026` operator index;
- manual diagnostics when a known Drive file appears missing;
- emergency one-file syncs;
- spreadsheet-based review by humans who prefer Sheet views;
- comparing legacy decisions with Firestore source-quality state.

It must not become the production backend queue.

## What Was Wrong With The Sheet-First Path

The B2 Apps Script only processes existing Sheet rows with:

```text
enrichment_status = NEEDS_AI
enrichment_status = AI_RATE_LIMITED
```

It does not scan Drive and does not append new files.

Therefore the row count in `Files` will not change when only B2 runs.

The deeper architectural issue is that Sheet state is not visible to the deployed
workers until imported into Firestore. Admin Web, content extraction, entity
extraction, review queues, context bundles and Obsidian projections operate from
Firestore, not from the Sheet.

## Current Backend Baseline

Cloud Run already contains the production indexing path:

```text
service: capital-drive-scanner
region: europe-west1
scheduler: capital-drive-scanner-daily
current MVP limit: 250 files
current MVP root: DRIVE_SCAN_ROOT_FOLDER_IDS
target: expand to multi-root or all-accessible Drive scan with persisted state
```

The immediate production task is to expand this scanner safely and make Firestore
`/files` the authoritative file inventory.

## B1 Drive Sync

Status:

```text
legacy / migration / diagnostic path
```

Script file:

```text
scripts/apps-script/capital_index_b1_drive_sync.gs
```

Responsibilities:

- list Drive files with Advanced Drive Service;
- compare each Drive `file_id` with the Sheet `file_id` column;
- append missing files;
- set default values:
  - `project = UNCATEGORIZED`
  - `action = REVIEW`
  - `value_score = 1`
  - `enrichment_status` by file type:
    - Docs, Sheets, Markdown, text, JSON, CSV: `NEEDS_AI`
    - images: `NEEDS_IMAGE_REVIEW`
    - PDFs: `NEEDS_PDF_REVIEW`
    - presentations: `NEEDS_PRESENTATION_REVIEW`
    - audio/video: `NEEDS_MEDIA_REVIEW`
    - unknown binary files: `NEEDS_FILE_REVIEW`
- continue with a time trigger if the scan cannot finish in one Apps Script run.

Performance constraints:

- B1 uses a 4 minute runtime budget to leave Apps Script enough time to write rows,
  save page token state, and create the continuation trigger.
- B1 intentionally does not call `Drive.Files.get()` for every parent folder while
  scanning. It writes `parent_folder_id` immediately and leaves non-root
  `parent_folder_name` blank. Folder names can be backfilled later in a separate
  unique-folder pass if needed.

Required Apps Script setup:

```text
Extensions -> Apps Script -> Services -> add Drive API
```

Run:

```text
startDriveFilesSync()
```

This is now the full manual audit path. It uses `allDrives` and is useful for
coverage checks, but it should not be the primary way to catch newly created
operator files.

For files created or modified after a full scan in "My Drive", run:

```text
syncRecentMyDriveFilesToSheet()
```

Compatibility alias:

```text
syncRecentDriveFilesToSheet()
```

This scans only the last 7 days in `corpora = user` by:

```text
createdTime >= cutoff OR modifiedTime >= cutoff
```

Use it for daily operation and immediately after creating new files. It appends
missing rows and assigns a safe `enrichment_status` by file type.

Recent Drive audit:

```text
auditRecentMyDriveFiles()
```

Compatibility alias:

```text
auditRecentDriveFiles()
```

This writes the `RECENT_MY_DRIVE_FILES` tab so the operator can verify what Drive
API returns for the recent My Drive window. The report includes `created_iso`,
`modified_iso`, `owned_by_me`, and `parents`.

Diagnostic search for one known missing file:

```text
findDriveFileForIndexDebug('exact or partial file name')
```

This writes `DRIVE_FILE_DEBUG_SEARCH` and marks whether each match is already in
the `Files` sheet.

Manual one-file sync:

```text
syncDriveFileById('file id or Drive URL')
```

Use this only to prove that a known file is visible to Drive API and can be added
to `Files`. If the file is trashed, the row is not deleted; it is marked for
review.

Incremental Drive Changes sync:

```text
initDriveChangesToken()
```

Run this once after the recent backfill is clean. It stores the current Drive
Changes cursor and does not backfill old changes.

Then, after creating/modifying files:

```text
syncDriveChangesToSheet()
```

This reads Drive changes after the stored token, appends new files, refreshes
basic metadata for changed files, and marks removed/trashed files for review. It
never deletes rows and never mutates Drive files.

Then B2 can run:

```text
startAiTaggingViaCloudRun()
```

Do not use the legacy direct-Gemini Apps Script `startAiTagging()` in production.
It hardcoded or directly referenced API keys and violates `docs/SECRETS_POLICY.md`.

## B2 Sheet Cloud Run Tagging

Status:

```text
legacy / migration / diagnostic path
```

The Apps Script Cloud Run client is allowed as a temporary way to classify rows
already present in the Sheet. It should not be the long-term AI classifier for the
knowledge base. The production classifier should read Firestore `/files` and write
AI proposal fields there.

Production AI classifier writes proposal fields such as:

```text
ai_proposed_project_id
ai_proposed_type
ai_summary
ai_value_score
ai_action
ai_confidence
ai_provider_id
ai_model_id
ai_evidence_file_ids
ai_proposed_at
```

Human or policy-approved decisions write authoritative fields such as:

```text
project_id
type
source_status
index_eligible
manual_override
approved_by
approved_at
```

Duplicate audit:

```text
auditFilesSheetDuplicates()
```

This creates/refreshes the `DUPLICATE_AUDIT` tab. It reports:

- exact duplicate rows by `file_id`;
- suspicious duplicate candidates by `file_name + parent_folder_id + size_bytes`.

The audit does not delete or merge rows. It only reports candidates for operator review.

Coverage audit:

```text
auditDriveVsSheetCoverage()
```

This compares unique Drive file IDs with unique Sheet file IDs and creates:

- `DRIVE_SHEET_COVERAGE`: summary counts;
- `MISSING_FROM_SHEET`: Drive files not present in `Files`;
- `STALE_IN_SHEET`: Sheet rows not seen in the current Drive scan;
- `DUPLICATE_FILE_IDS`: duplicate exact `file_id` rows in the Sheet.

Use this audit when `scanned` counts look larger than Sheet row counts. `scanned`
is not unique file count; coverage audit is the source of truth.

Duplicate row deletion:

```text
dedupeFilesSheetByFileId()
```

This deletes duplicate `Files` rows with the same `file_id`. It keeps the best row
by this priority:

- `AI_DONE`;
- `KEEP`;
- non-empty summary;
- non-`UNCATEGORIZED` project;
- higher value score;
- oldest row as fallback.

Before deleting, it writes deleted rows to `DEDUPLICATED_ROWS_ARCHIVE` and writes the
chosen keep/delete plan to `DEDUPLICATION_RESULT`.

It does not delete or mutate Drive files.

## Drive Labels Taxonomy

Create one Google Drive label:

```text
Capital Index
```

Recommended fields:

```text
Source Status:
  active
  needs_human_review
  do_not_index
  candidate_empty
  candidate_duplicate
  candidate_stale
  candidate_archive

Knowledge Eligible:
  yes
  no

Project:
  capital_index
  integra_motors
  axon_agency
  leaders_advocates
  maritime_wolf_advisory
  zolotov
  avoinvestgroup
  avouniverse
  trust100
  content_factory
  uncategorized

Sensitivity:
  PUBLIC_INTERNAL
  BUSINESS_CONFIDENTIAL
  FINANCIAL_RESTRICTED
  LEGAL_PRIVILEGED
  SECRET
  DO_NOT_INDEX

Cleanup Recommendation:
  keep
  review
  archive_candidate
  duplicate_candidate
  stale_candidate
  delete_candidate
```

## Label Authority

Drive Labels should override filename heuristics.

Priority order:

```text
Human approval / audit action
Drive Labels
CAPITAL_INDEX_2026 Sheet action
Folder policies
Rules-based classifier
Default: needs_human_review
```

## AI Classification for Labels

If available in the Workspace plan, enable Google Drive AI classification for the
`Capital Index` label. Use it only for initial suggestions, not final restricted
approval.

Rules:

- AI may suggest `Project`, `Source Status`, and `Cleanup Recommendation`.
- AI may not approve restricted reads by itself.
- AI may not set hard delete approval.
- Files labeled `SECRET` or `DO_NOT_INDEX` are blocked from extraction.

## Backend Integration

Next backend step:

1. Extend Drive scanner fields to include Drive label metadata.
2. Store raw label data on `/files/{file_id}.drive_labels`.
3. Map labels into:
   - `source_status`
   - `index_eligible`
   - `project_id`
   - `sensitivity_class`
   - cleanup candidate fields
4. Show labels in Admin UI.
5. Add drift checks:
   - Sheet says KEEP but Label says do_not_index;
   - Label says active but file is trashed;
   - file exists in Drive but missing from Sheet.

## Security

Do not hardcode Gemini or API keys in Apps Script source.

Production B2 flow:

```text
Apps Script
  -> Cloud Run /classify-sheet-row
  -> Secret Manager capital-gemini-api-key
  -> Gemini API
  -> Cloud Run response
  -> Sheet update
```

Apps Script file:

```text
scripts/apps-script/capital_index_b2_cloud_run_client.gs
```

Cloud Run service:

```text
capital-entity-extractor
endpoint: POST /classify-sheet-row
env:
  SHEET_CLASSIFIER_ENABLED=true
  AI_PROVIDER=gemini
  GEMINI_API_KEY_SECRET_NAME=capital-gemini-api-key
  GEMINI_MODEL_ID=gemini-2.5-flash
```

`AI_PROVIDER_ENABLED` can remain `false`; this keeps broad entity extraction disabled
while allowing the Sheet classifier endpoint through the separate
`SHEET_CLASSIFIER_ENABLED` flag.

Any API key that was pasted into chat or source code must be rotated.
