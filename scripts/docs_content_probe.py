"""Read a Google Doc via Docs API and print extracted text.

Usage:
    python scripts/docs_content_probe.py <document_id>
    python scripts/docs_content_probe.py <document_id> --output tests/fixtures/docs/doc_response.json

Auth: same DWD path as drive_changes_probe.py.
    Requires DOCS_SUBJECT_EMAIL (default: office@integrayachtsuae.com).

Env vars:
    DOCS_SUBJECT_EMAIL=office@integrayachtsuae.com
    DRIVE_SA_KEY_PATH=./keys/drive-sa.json   (optional; falls back to keyless ADC DWD)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import google.auth
import google.auth.transport.requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

PROJECT_ID = "capital-index-2026"
SERVICE_ACCOUNT_EMAIL = "capital-workspace-reader@capital-index-2026.iam.gserviceaccount.com"
DEFAULT_SUBJECT = "office@integrayachtsuae.com"
SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]
TOKEN_URL = "https://oauth2.googleapis.com/token"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _get_credentials(subject: str):
    sa_key_path = os.getenv("DRIVE_SA_KEY_PATH")
    if sa_key_path and Path(sa_key_path).exists():
        creds = service_account.Credentials.from_service_account_file(
            sa_key_path,
            scopes=SCOPES,
            subject=subject,
        )
        return creds

    # Keyless ADC + IAMCredentials signJwt DWD
    import time
    import urllib.parse

    import google.auth.transport.requests
    import requests as _requests

    adc_creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    adc_creds.refresh(google.auth.transport.requests.Request())
    adc_token = adc_creds.token

    now = int(time.time())
    claim_set = {
        "iss": SERVICE_ACCOUNT_EMAIL,
        "sub": subject,
        "scope": " ".join(SCOPES),
        "aud": TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    }

    sign_url = (
        f"https://iamcredentials.googleapis.com/v1/projects/-"
        f"/serviceAccounts/{SERVICE_ACCOUNT_EMAIL}:signJwt"
    )
    sign_resp = _requests.post(
        sign_url,
        headers={"Authorization": f"Bearer {adc_token}"},
        json={"payload": json.dumps(claim_set)},
    )
    sign_resp.raise_for_status()
    signed_jwt = sign_resp.json()["signedJwt"]

    token_resp = _requests.post(
        TOKEN_URL,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": signed_jwt,
        },
    )
    token_resp.raise_for_status()
    access_token = token_resp.json()["access_token"]

    from google.oauth2.credentials import Credentials
    return Credentials(token=access_token)


def fetch_doc(document_id: str, subject: str) -> dict:
    creds = _get_credentials(subject)
    service = build("docs", "v1", credentials=creds)
    return service.documents().get(documentId=document_id).execute()


def extract_text(doc: dict) -> str:
    parts: list[str] = []
    for element in doc.get("body", {}).get("content", []):
        if "paragraph" in element:
            for pe in element["paragraph"].get("elements", []):
                text_run = pe.get("textRun")
                if text_run:
                    parts.append(text_run.get("content", ""))
    return "".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read a Google Doc via Docs API.")
    parser.add_argument("document_id", help="Google Docs document ID")
    parser.add_argument("--output", type=Path, help="Save raw Docs API response JSON")
    args = parser.parse_args()

    subject = _env("DOCS_SUBJECT_EMAIL", DEFAULT_SUBJECT)

    try:
        doc = fetch_doc(args.document_id, subject)
    except HttpError as exc:
        print(f"Docs API error: {exc}", file=sys.stderr)
        return 1

    text = extract_text(doc)

    print(f"document_id : {doc.get('documentId')}")
    print(f"title       : {doc.get('title')}")
    print(f"chars       : {len(text)}")
    print(f"run_at      : {utc_now()}")
    print("---")
    print(text[:1000])
    if len(text) > 1000:
        print(f"... [{len(text) - 1000} more chars]")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"\nSaved to {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
