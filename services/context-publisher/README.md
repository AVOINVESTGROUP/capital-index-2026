# context-publisher

`context-publisher` turns approved Firestore knowledge state into controlled AI
context bundles and Obsidian projection previews.

It is the bridge between the indexed knowledge graph and any AI assistant. It is
not a raw prompt exporter and it does not bypass review.

## Contract

Input collections:

- `/files`
- `/extracted_text`
- `/entity_extractions`
- `/review_queue`
- `/cleanup_queue`

Output collections:

- `/source_evidence`
- `/claims`
- `/entities`
- `/relationships`
- `/context_bundles`
- `/vault_projections`

Only files with all of these fields may enter a bundle:

- `source_status = active`
- `index_eligible = true`
- `human_block != true`
- matching extracted text has `ai_context_allowed = true`

Generated claims, entities and relationships remain `review_status=proposed`.
Context bundles are written as `approval_status=draft` and
`requires_human_approval=true`.

## HTTP API

`GET /healthz`

Returns service health.

`POST /publish-context`

Builds a publication from Firestore or an explicit `source` payload.

Request fields:

- `source`: optional explicit source payload for tests/manual probes.
- `write`: optional boolean. Writes only work if the service environment allows
  request-gated writes.
- `bundle_type`: optional, defaults to `second_brain`.
- `limit`: optional Firestore read limit.
- `max_bundle_bytes`: optional bundle budget.
- `owner_profile`: optional owner profile when reading Firestore.
- `policy_snapshot_id`: optional policy snapshot id.

Write gates:

- `WRITE_ENABLED=true` allows writes for every request.
- `REQUEST_WRITE_ENABLED=true` plus request `"write": true` allows explicit
  request-gated writes.
- Default is dry-run.

## Obsidian Projection

The service creates `00_SECOND_BRAIN_INDEX.md` as a preview only. Generated
content is placed between protected markers:

```md
<!-- CAPITAL_INDEX:GENERATED_START -->
...
<!-- CAPITAL_INDEX:GENERATED_END -->
```

Manual notes stay outside the generated block and are not overwritten by this
service.

## Local Tests

```bash
python -m unittest services/context-publisher/tests/test_builder.py services/context-publisher/tests/test_firestore_writer.py services/context-publisher/tests/test_app.py -v
```

## Current Deployment

```text
service: capital-context-publisher
region: europe-west1
image: europe-west1-docker.pkg.dev/capital-index-2026/capital-workers/context-publisher:second-brain-20260529
write_enabled: false
request_write_enabled: true
```
