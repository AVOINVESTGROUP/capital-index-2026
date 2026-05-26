"""Create Drive Workspace Events subscription.

Keyless flow:
1. Use local ADC user credentials.
2. Call IAM Credentials signJwt for the workspace reader service account.
3. Exchange signed JWT for a Workspace OAuth token using domain-wide delegation.
4. Create Workspace Events subscription for the Drive test folder.
"""

from __future__ import annotations

import json
import time
from typing import Any

import google.auth
import google.auth.transport.requests
import requests

PROJECT_ID = "capital-index-2026"
SERVICE_ACCOUNT_EMAIL = "capital-workspace-reader@capital-index-2026.iam.gserviceaccount.com"
SUBJECT_USER = "office@integrayachtsuae.com"
DRIVE_TEST_FOLDER_ID = "1YHJ0YY4I_8QulKJR2O5S972_BK93NqMu"
PUBSUB_TOPIC = "projects/capital-index-2026/topics/capital-events-drive-test"

TOKEN_URL = "https://oauth2.googleapis.com/token"
CREATE_URL = "https://workspaceevents.googleapis.com/v1/subscriptions"
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]


def adc_access_token() -> str:
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    request = google.auth.transport.requests.Request()
    creds.refresh(request)
    return creds.token


def sign_jwt(access_token: str) -> str:
    now = int(time.time())
    payload = {
        "iss": SERVICE_ACCOUNT_EMAIL,
        "sub": SUBJECT_USER,
        "scope": " ".join(SCOPES),
        "aud": TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    }
    url = f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{SERVICE_ACCOUNT_EMAIL}:signJwt"
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": PROJECT_ID,
        },
        json={"payload": json.dumps(payload, separators=(",", ":"))},
        timeout=60,
    )
    if not resp.ok:
        raise RuntimeError(f"signJwt failed: {resp.status_code}\n{resp.text}")
    return resp.json()["signedJwt"]


def exchange_token(signed_jwt: str) -> str:
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": signed_jwt,
        },
        timeout=60,
    )
    if not resp.ok:
        raise RuntimeError(f"token exchange failed: {resp.status_code}\n{resp.text}")
    return resp.json()["access_token"]


def create_subscription(workspace_token: str) -> dict[str, Any]:
    body = {
        "targetResource": f"//drive.googleapis.com/files/{DRIVE_TEST_FOLDER_ID}",
        "eventTypes": [
            "google.workspace.drive.file.v3.created",
            "google.workspace.drive.file.v3.moved",
            "google.workspace.drive.file.v3.contentChanged",
            "google.workspace.drive.file.v3.deleted",
            "google.workspace.drive.file.v3.trashed",
            "google.workspace.drive.file.v3.untrashed",
            "google.workspace.drive.file.v3.renamed",
        ],
        "notificationEndpoint": {"pubsubTopic": PUBSUB_TOPIC},
        "payloadOptions": {"includeResource": False},
    }
    resp = requests.post(
        CREATE_URL,
        headers={
            "Authorization": f"Bearer {workspace_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": PROJECT_ID,
        },
        json=body,
        timeout=60,
    )
    if not resp.ok:
        raise RuntimeError(f"subscription create failed: {resp.status_code}\n{resp.text}")
    return resp.json()


def main() -> None:
    print("Getting local ADC token")
    token = adc_access_token()
    print("Signing domain-wide delegation JWT")
    signed = sign_jwt(token)
    print("Exchanging JWT for Workspace OAuth token")
    workspace_token = exchange_token(signed)
    print("Creating Workspace Events subscription")
    result = create_subscription(workspace_token)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
