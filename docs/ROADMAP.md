# ROADMAP

## Phase 0 — Repository and governance

- [x] Create repository scaffold
- [x] Create initial documentation
- [ ] Initialize Git
- [ ] Create GitHub remote
- [ ] Add architecture baseline
- [ ] Add ADRs
- [ ] Add environment templates

## Phase 0.1 — Drive Events POC

- [ ] Create GCP project
- [ ] Enable POC APIs
- [ ] Create Pub/Sub topic
- [ ] Create test Drive folder
- [ ] Subscribe to Drive events
- [ ] Test create/update/move/delete
- [ ] Document whether Workspace Events API is primary
- [ ] Document Drive changes API fallback

## Phase 0.5 — Migration planning

- [ ] Export current CAPITAL_INDEX_2026 Sheet
- [ ] Map current Vault structure
- [ ] Parse existing `00-overview.md` files
- [ ] Define project registry
- [ ] Define source registry

## Phase 1 — Event fabric

- [ ] event-ingestor
- [ ] metadata-loader
- [ ] nightly reconciler
- [ ] audit events

## Phase 2 — Policy and classification

- [ ] folder_policies
- [ ] source_registry
- [ ] policy-engine-worker
- [ ] review_queue

## Phase 3 — Extraction and graph

- [ ] content-extractor
- [ ] entity-extractor
- [ ] relationship-extractor
- [ ] graph-builder

## Phase 4 — Projection

- [ ] context-publisher
- [ ] vault-writer
- [ ] AI context bundles
