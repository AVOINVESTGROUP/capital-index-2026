# CAPITAL INDEX Admin Web

Next.js operator console for CAPITAL INDEX 2026.

## Current Scope

Route:

```text
/review
```

Capabilities:

```text
list Firestore /review_queue items
filter by status
inspect review item details
approve / reject / mark needs_content / close / reopen
write audit records to /review_actions
Google sign-in gate with server-side allowlist
```

## Security Boundary

Browser code does not access Firestore directly.

```text
Browser UI
  -> Firebase Auth ID token
  -> Next API routes
  -> Firebase Admin token verification
  -> server-side Firestore REST access
  -> /review_queue and /review_actions
```

Local development uses:

```text
gcloud auth application-default print-access-token
```

Production should use Cloud Run service identity.
Production API access requires `ADMIN_ALLOWED_EMAILS`.

Do not put service account keys, bot tokens, OAuth secrets or Secret Manager
values into `NEXT_PUBLIC_*`.

## Development

From repository root:

```text
npm install
npm run admin:web
```

Then open:

```text
http://localhost:3000/review
```

Required local auth:

```text
gcloud auth application-default login
gcloud auth application-default set-quota-project capital-index-2026
```
