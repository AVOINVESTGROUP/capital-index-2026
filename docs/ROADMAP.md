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

- [x] Create GCP project
- [x] Enable POC APIs
- [x] Create Pub/Sub topic
- [x] Create test Drive folder
- [ ] Subscribe to Drive events
- [x] Test file create
- [ ] Test file update
- [ ] Test file move
- [ ] Test file delete
- [x] Document whether Workspace Events API is primary
- [x] Document Drive changes API fallback

## Phase 0.2 — Repository hardening

- [x] Add secrets policy
- [ ] Add GitHub issue templates
- [ ] Add PR template
- [ ] Add branch protection rules
- [ ] Add docs lint workflow
- [ ] Add initial labels
- [ ] Add first issues for Phase 0.1

## Phase 0.5 — Migration planning

- [ ] Export current CAPITAL_INDEX_2026 Sheet
- [x] Document Google Workspace-native governance path
- [x] Add Apps Script B1 Drive -> Files sync for missing file rows
- [x] Add Apps Script B2 Cloud Run client without embedded secrets
- [x] Add Cloud Run `/classify-sheet-row` endpoint backed by Secret Manager
- [x] Run B1 sync and B2 Cloud Run tagging on live CAPITAL_INDEX_2026 Sheet
- [ ] Create Google Drive `Capital Index` label taxonomy
- [ ] Keep Sheet as migration/operator aid, not production source of truth
- [ ] Import legacy Sheet decisions into Firestore only as migration evidence
- [ ] Map current Vault structure
- [ ] Parse existing `00-overview.md` files
- [ ] Define project registry
- [ ] Define source registry
- [ ] Define folder policies
- [ ] Define first strict-domain folders

## Phase 0.6 — Drive-to-Firestore primary index

- [x] Deploy Cloud Run `capital-drive-scanner`
- [x] Add Cloud Scheduler `capital-drive-scanner-daily`
- [x] Verify controlled `/files` write from Drive scanner
- [x] Expand scanner beyond the initial single-root, 250-file MVP
- [x] Add all-accessible Drive scan mode with explicit operator limits
- [x] Deploy `all_drive` scheduled scan with `max_files=3000`
- [x] Keep broad-scan authoritative refetch disabled by default
- [ ] Add scan state and page-token persistence in Firestore
- [ ] Preserve manual source-quality overrides during scanner refresh
- [ ] Add Drive Label read/write integration for source quality where available
- [ ] Make Admin Source Files tab the authoritative correction surface
- [ ] Add scanner health and coverage metrics to admin progress dashboard

## Phase 0.7 — AI proposals before authority

- [ ] Add Firestore-backed file AI classifier worker
- [ ] Write AI output to proposal fields, not authoritative source fields
- [ ] Add proposal confidence, evidence file IDs and model/provider audit fields
- [ ] Route low-confidence or conflicting proposals to `/review_queue`
- [ ] Let admin UI accept, correct or reject proposals with `/source_quality_actions`
- [ ] Keep destructive actions and Drive mutations behind human approval

## Phase 1 — Event fabric

- [x] event-ingestor local fixture prototype
- [x] Cloud APIs enabled after billing
- [x] Artifact Registry repository created
- [x] baseline Pub/Sub topics and subscriptions created
- [x] event-ingestor internal Cloud Run container deployed write-disabled
- [x] event-ingestor Firestore write boundary added disabled by config
- [x] event-ingestor controlled Firestore test write
- [x] event-ingestor Pub/Sub execution model
- [x] event-ingestor publishes metadata jobs
- [x] metadata-loader local fixture prototype
- [x] metadata-loader Firestore write worker
- [x] metadata-loader Drive API authoritative refetch
- [x] metadata-loader publishes policy jobs
- [x] metadata-loader preserves human source-quality decisions during metadata refresh
- [x] Drive scanner/reconciler local controlled scan
- [x] Controlled `/files` write for first Drive inventory batch
- [x] Scheduled daily Drive scanner/reconciler
- [ ] production-grade incremental reconciler with persisted state
- [ ] audit events

## Phase 2 — Policy and classification

- [ ] folder_policies
- [ ] source_registry
- [x] policy-engine-worker local fixture prototype
- [x] policy-engine-worker Firestore-backed worker
- [x] policy-engine-worker publishes extraction jobs
- [ ] review_queue

## Phase 2.5 — Drive governance

- [x] Document Drive Governance decision before broad AI analysis
- [x] Add Drive Governance runbook
- [x] Define `/files` source quality fields
- [x] Define `/cleanup_queue` schema
- [x] Define `/cleanup_actions` schema
- [x] Define `/file_duplicates` schema
- [x] Add Drive Governance MVP fixtures
- [x] Add JSON Schema validation tests for governance fixtures
- [x] Build drive-governance local fixture prototype
- [x] Detect empty candidates
- [x] Detect duplicate-name candidates
- [x] Detect stale/version candidates
- [x] Detect unknown-project candidates
- [x] Add controlled Firestore write boundary for `/cleanup_queue` and `/file_duplicates`
- [x] Add Cleanup Queue admin UI
- [x] Add Source Files admin approval UI for `/files`
- [x] Add Knowledge admin UI for extracted content and AI findings
- [x] Add admin progress dashboard for Drive -> Knowledge pipeline
- [x] Add rules-based source auto-classifier
- [x] Run controlled source auto-classification on first 250 scanned files
- [x] Deploy drive-governance Cloud Run worker write-disabled
- [x] Run controlled Firestore write to populate `/cleanup_queue`
- [x] Add scheduled governance execution
- [ ] Add event-driven governance execution after extraction
- [x] Block entity extraction unless `source_status=active` and `index_eligible=true`
- [ ] Add human-approved archive/move/label workflow
- [ ] Keep hard delete forbidden

## Phase 3 — Extraction and graph

- [x] content-extractor local Docs API prototype
- [x] content-extractor Firestore-backed worker
- [x] review_queue for empty extraction results
- [x] content-extractor Markdown/plain text support
- [x] content-extractor Google Sheets support
- [x] controlled live Markdown extraction write
- [x] controlled live Google Sheets extraction write
- [x] entity-extractor Drive Governance gate
- [x] entity-extractor provider-neutral AI extraction contract
- [x] entity-extractor Firestore read/write worker scaffold
- [x] Deploy entity-extractor Cloud Run worker write-disabled
- [x] entity-extractor OpenAI adapter behind Secret Manager
- [x] entity-extractor Gemini adapter behind Secret Manager
- [x] entity-extractor controlled live AI provider test
- [x] entity-extractor controlled Firestore write to `/entity_extractions`
- [x] approved-source content extraction batch script
- [x] controlled approved-source content extraction batch write
- [x] controlled entity extraction batch write after auto-classification
- [x] entity extraction batch/retry script
- [ ] entity-extractor live AI provider enabled in production
- [ ] relationship-extractor
- [ ] graph-builder

## Phase 4 — Projection

- [ ] context-publisher
- [ ] vault-writer
- [ ] AI context bundles
- [ ] owner profile context bundle
- [ ] project context bundles
- [ ] relationship graph bundle
- [ ] recent changes bundle
- [ ] evidence bundle with multiple Drive links per answer
- [ ] admin preview/approve flow for context bundles

## Phase 5 — Review and operations

- [x] review_queue markdown projection
- [x] admin-web Next.js scaffold
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
