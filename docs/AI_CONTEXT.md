# AI_CONTEXT — Capital Orchestrator

## Project

CAPITAL INDEX 2026

## Current task

Move from Sheet-first migration tooling to the production Drive-to-Firestore
indexing and governance path.

## Operating rule

Do not treat Google Sheet or Apps Script as the production backend queue.
Firestore `/files` is the operational source of truth. AI writes proposals;
policy or human approval writes authoritative decisions.

## Current files

```text
README.md
docs/ROADMAP.md
docs/AI_OPERATING_INSTRUCTIONS.md
docs/runbooks/GOOGLE_WORKSPACE_NATIVE_GOVERNANCE.md
docs/runbooks/DRIVE_GOVERNANCE.md
docs/adr/0005-drive-scanner-firestore-primary-index.md
services/drive-scanner/
apps/admin-web/
```

## Next actions

1. Expand `capital-drive-scanner` beyond the initial single-root, 250-file MVP.
2. Preserve manual source-quality overrides during scanner refresh.
3. Add Firestore-backed AI classifier proposals.
4. Add Admin Web proposal review/correction.
5. Build context bundles from approved Firestore state.
