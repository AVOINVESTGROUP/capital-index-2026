# ADR 0006: Vertex RAG as the Knowledge Plane

## Status

Accepted.

## Context

CAPITAL INDEX previously treated Firestore context bundles as the main way to
feed AI systems. That is useful for controlled summaries, review and audit, but
it is not enough for a full second brain because important facts can remain in
source files and never appear in short summaries.

The project now has a Google-native RAG corpus:

```text
project: capital-index-2026
region: us-central1
corpus: second-brain-vault
corpus_id: 6241865938233196544
source: Google Drive / 00-Vault
prompt: second-brain-vault-base
```

## Decision

Vertex RAG Engine is the primary knowledge retrieval plane for Obsidian/Drive
source material.

Firestore and Admin Web remain the control plane:

- approval state;
- source quality;
- context bundle review;
- Vault projection preview;
- audit trail;
- human approval before persistent memory or Vault writes.

## Consequences

- AI answers should retrieve source evidence from Vertex RAG instead of relying
  only on compressed summaries.
- Context bundles remain useful as curated memory snapshots, not as the only
  source of truth.
- Obsidian writes remain proposal-based until a separate approved writer flow is
  implemented.
- Admin Web must expose RAG corpus status and link operators back to Vertex
  Agent Studio for testing.

## Operating Rule

```text
Drive / Obsidian source files -> Vertex RAG -> grounded AI answer
Firestore/Admin -> review, approval, audit, memory publication
Vault writer -> approved markdown projection only
```
