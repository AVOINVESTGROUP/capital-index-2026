# HANDOFF — CAPITAL INDEX 2026

## Purpose

This file is the transition note for continuing CAPITAL INDEX 2026 in another chat or with another AI/operator.

The next assistant must not guess prior state. Use this file as the current operational baseline.

---

## 1. Current project status

Repository created and pushed:

```text
GitHub: AVOINVESTGROUP/capital-index-2026
Local path: C:\Dev\capital_orc
Default branch: main
```

GCP project exists:

```text
project_id: capital-index-2026
project_number: 745677061768
organization: fixer.guru
```

Firebase / Firestore created correctly:

```text
Firebase project: capital-index-2026
Firestore database: (default)
Firestore location: eur3
Firestore type: FIRESTORE_NATIVE
Firestore edition: STANDARD
```

Firestore rules/indexes deployed:

```text
firestore.rules: locked baseline
firestore.indexes.json: empty baseline
```

Initial Firestore seed completed successfully.

---

## 2. Repository files already created

Root AI/operator files:

```text
AGENTS.md
GEMINI.md
CLAUDE.md
CHATGPT.md
CODEX.md
README.md
.env.example
.gitignore
firebase.json
.firebaserc
firestore.rules
firestore.indexes.json
requirements.txt
```

Docs:

```text
docs/ARCHITECTURE.md
docs/STEPS.md
docs/ROADMAP.md
docs/AI_CONTEXT.md
docs/AI_OPERATING_INSTRUCTIONS.md
docs/SKILLS.md
docs/QUALITY_GATES.md
docs/PROJECT_STRUCTURE_STANDARD.md
docs/INTAKE_PROTOCOL.md
docs/SECRETS_POLICY.md
docs/runbooks/FIREBASE_BASELINE.md
docs/runbooks/DRIVE_EVENTS_POC.md
```

Scripts:

```text
scripts/seed_firestore_baseline.py
scripts/create_workspace_drive_subscription.py
scripts/drive_changes_probe.py
```

Fixtures:

```text
tests/fixtures/drive-events/.gitkeep
```

---

## 3. Important policy decisions

### 3.1 Secrets

All real secrets must go to Google Secret Manager.

Do not use service account JSON keys as the normal path.

Forbidden as source of truth:

```text
local secrets/ folder
repository
Vault
Google Sheets
Firestore
Apps Script Properties for production secrets
```

Preferred auth model:

```text
local dev: gcloud ADC + IAMCredentials signJwt
production: service account identity / Workload Identity / Secret Manager only where required
```

### 3.2 Workspace Events status

Workspace Events POC is currently paused.

Verified:

```text
Pub/Sub topic exists
Google Drive system publisher binding fixed
User token has Drive scope
DWD service-account flow signs JWT and exchanges token
```

Still failing:

```text
Workspace Events subscription with user token:
  INVALID_PUBSUB_TOPIC
  reason: token/app project mismatch

Workspace Events subscription with DWD token:
  TARGET_RESOURCE_ACCESS_DENIED
  reason: Drive target resource access denied
```

Decision for now:

```text
Do not continue fighting Workspace Events auth.
Use Drive API changes.list / startPageToken polling as fallback POC path.
```

---

## 4. Google Workspace baseline

Test Drive folder created:

```text
name: CAPITAL_INDEX_EVENT_TEST
folder_id: 1YHJ0YY4I_8QulKJR2O5S972_BK93NqMu
url: https://drive.google.com/drive/folders/1YHJ0YY4I_8QulKJR2O5S972_BK93NqMu
```

Service accounts created:

```text
capital-workspace-reader@capital-index-2026.iam.gserviceaccount.com
capital-vault-writer@capital-index-2026.iam.gserviceaccount.com
firebase-adminsdk-fbsvc@capital-index-2026.iam.gserviceaccount.com
```

Domain-Wide Delegation client IDs:

```text
capital-workspace-reader client_id: 105249244589764651440
capital-vault-writer client_id: 117734605799955226260
```

Reader scopes intended in Admin Console:

```text
https://www.googleapis.com/auth/drive.metadata.readonly
https://www.googleapis.com/auth/drive.readonly
https://www.googleapis.com/auth/spreadsheets.readonly
https://www.googleapis.com/auth/documents.readonly
https://www.googleapis.com/auth/gmail.readonly
```

Writer scope intended in Admin Console:

```text
https://www.googleapis.com/auth/drive.file
```

---

## 5. Enabled APIs

Enabled APIs observed:

```text
docs.googleapis.com
drive.googleapis.com
driveactivity.googleapis.com
firestore.googleapis.com
gmail.googleapis.com
iamcredentials.googleapis.com
pubsub.googleapis.com
sheets.googleapis.com
workspaceevents.googleapis.com
firebase.googleapis.com
firebaserules.googleapis.com
bigquery.googleapis.com
storage.googleapis.com
logging.googleapis.com
monitoring.googleapis.com
```

Billing is not yet attached, so these were blocked/deferred:

```text
run.googleapis.com
cloudbuild.googleapis.com
artifactregistry.googleapis.com
containerregistry.googleapis.com
```

Billing status:

```text
Main paid account hit billing quota.
User plans to create/use a new billing account later.
Do not depend on Cloud Run / Cloud Build until billing is fixed.
```

---

## 6. Firestore seeded documents

Seed script already run successfully:

```text
python scripts/seed_firestore_baseline.py
```

Seeded:

```text
/system_config/model_routing
/system_config/vector_backend
/system_config/throttling
/project_registry/capital_index
/source_registry/vault_root
/source_registry/drive_event_test
/security_policies/default_locked
/folder_policies/vault_root
/folder_policies/drive_event_test
```

---

## 7. Current GitHub issues

Issue #1:

```text
Phase 0.1 — Drive Events POC
Status: Workspace Events path paused; fallback Drive Changes probe is next.
```

Issue #2:

```text
Phase 0.2 — Firebase baseline setup
Status: Firestore created correctly in eur3, rules deployed, seed completed.
```

Issue #3:

```text
Phase 0.3 — Workspace baseline setup
Status: test folder created, service accounts created, DWD client IDs known.
```

---

## 8. Current next action

Run Drive Changes API probe.

Local commands:

```powershell
git pull origin main
pip install -r requirements.txt
python scripts/drive_changes_probe.py
```

Expected first run:

```text
Initializes page token.
No changes returned by design.
Writes tests/fixtures/drive-events/probe_*.json
```

Then manually create or edit a file inside:

```text
CAPITAL_INDEX_EVENT_TEST
folder_id: 1YHJ0YY4I_8QulKJR2O5S972_BK93NqMu
```

Then run again:

```powershell
python scripts/drive_changes_probe.py
```

Expected second run:

```text
changes > 0
folder_children >= 1
fixture JSON written under tests/fixtures/drive-events/
```

If 403 occurs:

```text
Check DWD scopes for capital-workspace-reader client ID 105249244589764651440.
The required scope is drive.readonly.
```

---

## 9. Do not repeat these mistakes

1. Do not create Firebase project with suffix like `capital-index-2026-29d10`.
   Correct project is `capital-index-2026`.

2. Do not create Firestore in `nam5`.
   Correct location is `eur3`.

3. Do not try to create service account JSON keys.
   Org policy blocks key creation and that is correct.

4. Do not keep fighting Workspace Events until exact auth/app requirements are verified.
   Use Drive Changes API fallback now.

5. Do not commit secrets or local tokens.

6. Do not invent Drive/Vault paths. Verify parent chain first.

---

## 10. User working style and constraint

The user wants execution, not commentary.

Important behavior rules for the next assistant:

```text
Do the task directly.
Do not expand scope unless required.
Do not claim completion if a tool failed.
Do not invent paths or state.
When giving commands, give only the next concrete command block.
When blocked, state blocker and the next decision.
```

The user strongly prefers:

```text
short operational answers
clear next action
no generic explanations
no repeated apologies
no artificial simplification of architecture
```

---

## 11. One-line continuation prompt

Continue CAPITAL INDEX from HANDOFF.md. Current next step: run `scripts/drive_changes_probe.py`, verify Drive Changes API access and fixture output, then update GitHub issue #1 with the result.
