# ADR-0003: Drive Governance Before AI Analysis

Date: 2026-05-27

Status: Accepted

## Context

CAPITAL INDEX reads Google Drive and uses file content as evidence for project state, relationships,
AI context, and future graph extraction.

Google Drive is not guaranteed to be clean:

- old commercial offers can remain next to current offers;
- files can be duplicated across folders;
- drafts and final versions can coexist;
- empty or broken documents can look like valid sources;
- temporary files can be indexed accidentally;
- outdated files can mislead AI into treating old facts as current facts.

If AI reads all available files without a source-quality gate, it can:

- treat stale prices as current;
- treat duplicate files as multiple independent evidence sources;
- confuse draft contracts with signed contracts;
- overstate confidence because copies repeat the same evidence;
- pollute AI context bundles with irrelevant files.

## Decision

CAPITAL INDEX must introduce Drive Governance before broad AI analysis and graph extraction.

Every Drive file must receive source-quality fields before it can be used as AI evidence:

```text
source_status
index_eligible
governance_status
governance_reason
governance_confidence
```

Allowed source statuses:

```text
active
candidate_duplicate
candidate_stale
candidate_empty
candidate_archive
do_not_index
needs_human_review
```

Only this condition allows a file to enter AI analysis:

```text
source_status = active
index_eligible = true
policy_allowed = true
human_block = false
```

Drive Governance recommendations are advisory. The system may recommend:

```text
keep_active
mark_duplicate
archive
move_to_review
do_not_index
needs_review
```

The system must not perform hard delete automatically.

Archive, move, relabel, and delete actions require:

```text
Policy Engine decision
human approval
audit log entry
```

## Consequences

Entity extraction and graph writing are blocked for files that are duplicate, stale, empty, archived,
unknown, or manually blocked.

The next implementation phase is not entity extraction. The next implementation phase is the Drive
Governance MVP:

```text
file metadata inventory
empty candidate detection
duplicate candidate detection
stale/version candidate detection
cleanup_queue
cleanup_actions
admin approval surface
```

## Firestore Collections

Drive Governance introduces:

```text
/cleanup_queue
/cleanup_actions
/file_duplicates
```

It extends:

```text
/files/{file_id}
```

## Non-Goals

This ADR does not approve automatic deletion.

This ADR does not make AI the authority for file cleanup.

This ADR does not replace Policy Engine, Review Orchestrator, or Human Approval.

## Safety Rule

```text
Recommend first.
Approve manually.
Mutate Drive only after policy + human approval.
Never hard-delete automatically.
```
