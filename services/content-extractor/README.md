# content-extractor

Phase 3 worker for reading file content and producing an extraction result.

Supported formats:

```text
Google Docs: application/vnd.google-apps.document
Google Sheets: application/vnd.google-apps.spreadsheet
Markdown/plain text: text/markdown, text/plain, .md, .markdown, .txt
```

Current scope:

```text
input: policy decision batch or Pub/Sub push envelope
output: extracted plain text batch + constraints carried forward
Cloud Run: POST /extract-content and POST /pubsub/extraction
Firestore: /extracted_text/{file_id}, gated by WRITE_ENABLED=true
Docs API read: gated by DOCS_READ_ENABLED=true
Sheets API read: gated by SHEETS_READ_ENABLED=true
Drive plain-text download: gated by DRIVE_READ_ENABLED=true
Review queue: /review_queue/{review_id}, gated by REVIEW_QUEUE_ENABLED=true
```

The worker writes to Firestore only when `WRITE_ENABLED=true`.
It calls Workspace read APIs only when the matching read flag is enabled.
It writes review items only when `REVIEW_QUEUE_ENABLED=true`.

## Test

```powershell
python -m unittest `
  services/content-extractor/tests/test_docs_reader.py `
  services/content-extractor/tests/test_extraction.py `
  services/content-extractor/tests/test_firestore_writer.py `
  services/content-extractor/tests/test_pubsub.py `
  services/content-extractor/tests/test_review_queue.py
```

## Probe (live Docs API call)

```powershell
python scripts/docs_content_probe.py 1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM
```

Save raw Docs API response as fixture:

```powershell
python scripts/docs_content_probe.py 1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM `
  --output tests/fixtures/docs/doc_response_20260526T105738Z.json
```

## Extraction result fields

```text
schema_version       capital.extracted_text.v1
file_id              Drive file ID
plan_id              from extraction plan
sensitivity_class    carried from policy decision
text_only            true — no raw binary content
embedding_allowed    carried from policy decision
vault_publish_allowed carried from policy decision
ai_context_allowed   carried from policy decision
doc_title            from Docs API
char_count           length of extracted text
text                 plain text
next_action          classify | review_required
```
