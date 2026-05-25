# STEPS — execution log

## Current status

Repository and documentation foundation.

## Step 001 — Create repository scaffold

Status: prepared

Artifacts:

```text
README.md
docs/ARCHITECTURE.md
docs/STEPS.md
docs/ROADMAP.md
docs/AI_CONTEXT.md
docs/adr/0001-repository-start.md
.env.example
.gitignore
```

## Step 002 — Initialize Git

Commands:

```bash
git init
git add .
git commit -m "Initialize CAPITAL INDEX repository"
```

## Step 003 — Create remote repository

Manual or GitHub CLI:

```bash
gh repo create capital-index-2026 --private --source=. --remote=origin --push
```

## Step 004 — Create GCP project

```bash
gcloud projects create capital-index-2026 --name="CAPITAL INDEX 2026"
gcloud config set project capital-index-2026
```

## Step 005 — Enable POC APIs only

```bash
gcloud services enable \
  pubsub.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  driveactivity.googleapis.com \
  workspaceevents.googleapis.com \
  drive.googleapis.com
```

## Step 006 — Create Pub/Sub test topic

```bash
gcloud pubsub topics create capital-events-drive-test
gcloud pubsub subscriptions create capital-events-drive-test-sub \
  --topic=capital-events-drive-test
```
