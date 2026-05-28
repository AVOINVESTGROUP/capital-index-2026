# FIREBASE_BASELINE.md — CAPITAL INDEX 2026

## Status

Firestore database created manually in Firebase Console.

## Project

```text
Firebase project: capital-index-2026
GCP project: capital-index-2026
Firestore database: (default)
Location: eur3 (Europe)
Plan: Spark until billing is attached
```

## Purpose

Firebase is used as the operational Firestore layer and local emulator environment for CAPITAL INDEX.

Firebase is not a separate source of truth outside the Firestore schema defined by CAPITAL INDEX.

## Baseline files

```text
.firebaserc
firebase.json
firestore.rules
firestore.indexes.json
```

## Security baseline

Firestore rules are locked by default:

```text
allow read, write: if false;
```

Server-side workers should use IAM / Admin SDK. Client access must not be opened until an explicit security model is approved.

## Local setup

```powershell
npm install -g firebase-tools
firebase login
firebase projects:list
firebase use capital-index-2026
firebase emulators:start --only firestore
```

## Deploy rules and indexes

```powershell
firebase deploy --only firestore:rules,firestore:indexes
```

## Next tasks

```text
1. Pull latest repo changes.
2. Verify Firebase CLI project selection.
3. Deploy locked Firestore rules.
4. Create initial Firestore seed script for system_config, project_registry and source_registry.
```

## Latest deploy verification status

`firebase deploy --only firestore:rules,firestore:indexes --project capital-index-2026`
completed successfully after Firebase CLI reauth.

```text
firestore.rules compiled successfully
firestore.indexes.json deployed successfully for (default)
rules released to cloud.firestore
```
