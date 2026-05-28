# SECRETS_POLICY - CAPITAL INDEX 2026

## Purpose

This document defines where secrets may live and how applications may use them.

Rule:

```text
Real secrets go to Google Secret Manager.
Private business data does not go to Secret Manager by default.
```

## What Is A Secret

These values are secrets:

```text
API keys for paid/private APIs
OAuth client secrets
refresh tokens
Telegram bot tokens
private keys
service account JSON keys
database passwords
webhook signing secrets
third-party integration tokens
```

Allowed storage:

```text
Google Secret Manager
Cloud Run secret environment variables
Cloud Run secret volume mounts
local developer ADC outside the repository
```

Forbidden storage:

```text
Git repository
Firestore
Google Sheets
Google Drive / Vault
Apps Script Properties for production
local secrets/ as source of truth
frontend bundle
browser localStorage
browser sessionStorage
```

## What Is Private Data

These values can be private, sensitive, or restricted, but they are not
automatically "secrets":

```text
Drive file ids
Drive file names
document metadata
document text
business project metadata
extraction results
review queue items
policy decisions
relationships and graph facts
```

Allowed storage:

```text
Google Drive
Firestore
BigQuery
Cloud Storage
generated projections with Policy Engine approval
```

Access must be controlled by:

```text
Policy Engine
Firestore rules or server-side IAM
Review Orchestrator
Human Approval
Audit Log
```

## Service Account Keys

Normal production path:

```text
Cloud Run service account identity
IAM permissions
IAMCredentials signJwt for Domain-Wide Delegation
Secret Manager only when a real third-party secret is required
```

Do not create service account JSON keys as the normal path.

If a temporary local key is ever required for emergency debugging:

```text
1. Do not commit it.
2. Keep it outside the repository when possible.
3. If placed under local secrets/, confirm secrets/ is ignored by git.
4. Delete it after use.
5. Rotate/revoke it if exposure is suspected.
```

Current repository guard:

```text
secrets/
*.key
*.pem
service-account*.json
.env
.env.*
```

are ignored by `.gitignore`.

## Next Admin Web Rules

The admin web app is a browser application. Browser code is public from a
security point of view.

Allowed in browser:

```text
Firebase public project config
public application id
public auth domain
non-secret feature flags
current UI route
user-facing status labels
```

Forbidden in browser:

```text
service account credentials
Google OAuth client secret
refresh tokens
bot tokens
Secret Manager values
admin SDK credentials
unfiltered SECRET / DO_NOT_INDEX content
```

The admin web app must use this boundary:

```text
Browser UI
  -> Next server route / server action
  -> server-side auth and policy check
  -> Firestore / Cloud Run worker
```

The browser must not write restricted operational state directly unless that
path has explicit security rules, auth checks, and audit logging.

## Environment Variables

Naming convention:

```text
NEXT_PUBLIC_* = may be exposed to browser
without NEXT_PUBLIC_ = server-only
```

Never put a real secret in a `NEXT_PUBLIC_*` variable.

Examples:

```text
NEXT_PUBLIC_FIREBASE_PROJECT_ID=capital-index-2026
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=capital-index-2026.firebaseapp.com
FIREBASE_ADMIN_PROJECT_ID=capital-index-2026
```

`NEXT_PUBLIC_FIREBASE_*` values are configuration, not secrets.

Server-only values must stay server-side and come from Secret Manager or runtime
identity, not from committed files.

## Firestore Rules

Current baseline:

```text
allow read, write: if false;
```

This is correct for the current server-worker architecture.

Before the admin web app reads or writes Firestore directly from the browser,
the project must define:

```text
Firebase Auth provider
allowed operator identities
read paths
write paths
audit requirements
restricted content exclusions
```

Default admin web implementation should use Next server routes first.

## Audit Requirements

Any operation that changes review state, approval state, policy state, or
publication state must record:

```text
action_id
actor_id
actor_type
source
target_collection
target_id
previous_status
new_status
reason
note
created_at
```

Agents may recommend actions but may not approve restricted actions on their own.

## Immediate Checklist

Before adding a new integration:

```text
1. Decide whether the value is a secret or private data.
2. If secret, store it in Google Secret Manager.
3. If private data, store it in the correct data system and protect it by policy.
4. Keep server credentials out of browser bundles.
5. Add audit logging for human approvals and restricted state changes.
```
