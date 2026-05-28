# ADR-0004: Legacy CAPITAL_INDEX_2026 as Curated Source

Date: 2026-05-28

## Status

Accepted

## Context

CAPITAL INDEX already has a legacy curated index in `CAPITAL_INDEX_2026 - Files (3).csv`
and the related Google Sheet / Apps Script path. That index contains file metadata,
project attribution, summaries, value scores, enrichment state, and operator-facing
actions such as `KEEP`, `REVIEW`, and `DELETE`.

The newer Drive scanner is useful for inventory and drift detection, but treating raw
Drive inventory as the first knowledge source creates noise: old context snapshots,
temporary files, duplicates, prompts, and low-value files can enter analysis before the
operator has approved the source set.

## Decision

The legacy `CAPITAL_INDEX_2026` index is the primary curated source for the first
production knowledge base migration.

Drive scanner remains secondary:

- it discovers new or changed files;
- it reconciles missing metadata;
- it detects drift from the curated index;
- it feeds cleanup recommendations;
- it does not decide what enters the knowledge base by itself.

Mapping from legacy index to Firestore source quality:

| Legacy action | Source status | Index eligible | Meaning |
|---|---|---:|---|
| `KEEP` | `active` | true | Approved source for knowledge extraction |
| `REVIEW` | `needs_human_review` | false | Needs grouped or manual decision |
| `DELETE` | `candidate_archive` | false | Cleanup candidate, no automatic deletion |
| empty action | `needs_human_review` | false | Unknown legacy decision |

`AI_DONE` means the legacy system already produced enrichment, but it does not by
itself grant new AI read approval. The source must still be `KEEP` or later approved.

## Consequences

- The system must import the legacy index before broad Drive analysis.
- Admin UI counts should be based on imported `/files` source quality, not only on
the current partial Drive scan.
- Content extraction and entity extraction must only read `active` and
`index_eligible=true` files.
- Cleanup suggestions can use the full Drive scanner, but deletion remains forbidden
without human approval and audit log.

## Next Implementation Step

Create a legacy index importer that reads `CAPITAL_INDEX_2026 - Files (3).csv`,
maps rows into `/files`, records source-quality audit actions, and runs in dry-run by
default. Only `--write` updates Firestore.
