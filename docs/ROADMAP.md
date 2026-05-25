# ROADMAP

## Phase 0 — Repository and governance

- [x] Create repository scaffold
- [x] Create initial documentation
- [x] Initialize Git
- [x] Create GitHub remote
- [x] Add architecture baseline
- [x] Add ADRs
- [x] Add environment templates
- [x] Add root AI provider instructions: `GEMINI.md`, `CLAUDE.md`, `CHATGPT.md`, `CODEX.md`
- [x] Add agent registry: `AGENTS.md`
- [x] Add skills catalog: `docs/SKILLS.md`
- [x] Add quality gates: `docs/QUALITY_GATES.md`
- [x] Add project structure standard: `docs/PROJECT_STRUCTURE_STANDARD.md`
- [x] Add intake protocol: `docs/INTAKE_PROTOCOL.md`

## Phase 0.1 — Drive Events POC

- [ ] Create GCP project
- [ ] Enable POC APIs
- [ ] Create Pub/Sub topic
- [ ] Create test Drive folder
- [ ] Subscribe to Drive events
- [ ] Test file create
- [ ] Test file update
- [ ] Test file move
- [ ] Test file delete
- [ ] Document whether Workspace Events API is primary
- [ ] Document Drive changes API fallback

## Phase 0.2 — Repository hardening

- [ ] Add GitHub issue templates
- [ ] Add PR template
- [ ] Add branch protection rules
- [ ] Add docs lint workflow
- [ ] Add initial labels
- [ ] Add first issues for Phase 0.1

## Phase 0.5 — Migration planning

- [ ] Export current CAPITAL_INDEX_2026 Sheet
- [ ] Map current Vault structure
- [ ] Parse existing `00-overview.md` files
- [ ] Define project registry
- [ ] Define source registry
- [ ] Define folder policies
- [ ] Define first strict-domain folders

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

## Phase 5 — Review and operations

- [ ] review-orchestrator
- [ ] approval channels
- [ ] cost-controller
- [ ] observability

## Phase 6 — Universal AI Gateway

- [ ] ai-gateway
- [ ] ai_providers registry
- [ ] ai_agents registry
- [ ] context delivery mechanisms
- [ ] multi-agent execution modes
