"""Keyless Domain-Wide Delegation helpers for Google Workspace APIs."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import google.auth
import google.auth.transport.requests
import requests
from google.oauth2 import credentials as oauth_credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build

PROJECT_ID = "capital-index-2026"
SERVICE_ACCOUNT_EMAIL = "capital-workspace-reader@capital-index-2026.iam.gserviceaccount.com"
DEFAULT_SUBJECT = "office@integrayachtsuae.com"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _adc_token() -> str:
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    request = google.auth.transport.requests.Request()
    creds.refresh(request)
    return creds.token


def _sign_jwt(access_token: str, subject: str, scopes: list[str]) -> str:
    now = int(time.time())
    claims = {
        "iss": SERVICE_ACCOUNT_EMAIL,
        "sub": subject,
        "scope": " ".join(scopes),
        "aud": TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    }
    url = f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{SERVICE_ACCOUNT_EMAIL}:signJwt"
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": PROJECT_ID,
        },
        json={"payload": json.dumps(claims, separators=(",", ":"))},
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(f"signJwt failed: {response.status_code}\n{response.text}")
    return response.json()["signedJwt"]


def _exchange_jwt(signed_jwt: str) -> str:
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": signed_jwt,
        },
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(f"JWT token exchange failed: {response.status_code}\n{response.text}")
    return response.json()["access_token"]


def workspace_credentials(scopes: list[str]) -> Any:
    subject = _env("DRIVE_SUBJECT_EMAIL", DEFAULT_SUBJECT)
    key_path = _env("DRIVE_SA_KEY_PATH")

    if key_path and Path(key_path).exists():
        return service_account.Credentials.from_service_account_file(
            key_path,
            scopes=scopes,
        ).with_subject(subject)

    signed_jwt = _sign_jwt(_adc_token(), subject or DEFAULT_SUBJECT, scopes)
    return oauth_credentials.Credentials(token=_exchange_jwt(signed_jwt))


def build_drive_service() -> Any:
    return build("drive", "v3", credentials=workspace_credentials(DRIVE_SCOPES), cache_discovery=False)
