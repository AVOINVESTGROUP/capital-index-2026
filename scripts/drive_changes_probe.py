"""Probe Google Drive Changes API for CAPITAL INDEX.

Purpose:
1. Verify Drive API access.
2. Initialize or read a persisted Drive startPageToken.
3. List Drive changes since the last saved token.
4. Filter one-level changes related to CAPITAL_INDEX_EVENT_TEST folder.
5. Save a JSON fixture under tests/fixtures/drive-events/.

Env vars:
    DRIVE_FOLDER_ID=1YHJ0YY4I_8QulKJR2O5S972_BK93NqMu
    DRIVE_SUBJECT_EMAIL=office@integrayachtsuae.com

Optional:
    DRIVE_SA_KEY_PATH=./keys/drive-sa.json
    DRIVE_ID=<shared drive id>
    DRIVE_STATE_PATH=tests/fixtures/drive-events/.page_token.json
    DRIVE_FIXTURES_DIR=tests/fixtures/drive-events

Auth modes:
    1. If DRIVE_SA_KEY_PATH exists, use service account key + DWD.
    2. Otherwise, use local ADC + IAMCredentials signJwt keyless DWD.

Known limitations:
    - Folder filter is one-level only: it checks whether folder_id is directly in file.parents.
    - First run initializes token and returns no changes by design.
    - Domain-Wide Delegation must allow drive.readonly for the service account client ID.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import google.auth
import google.auth.transport.requests
import requests
from google.oauth2 import credentials as oauth_credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

PROJECT_ID = "capital-index-2026"
SERVICE_ACCOUNT_EMAIL = "capital-workspace-reader@capital-index-2026.iam.gserviceaccount.com"
DEFAULT_SUBJECT = "office@integrayachtsuae.com"
DEFAULT_FOLDER_ID = "1YHJ0YY4I_8QulKJR2O5S972_BK93NqMu"

TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

DEFAULT_STATE_PATH = Path("tests/fixtures/drive-events/.page_token.json")
DEFAULT_FIXTURES_DIR = Path("tests/fixtures/drive-events")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def get_adc_token() -> str:
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    request = google.auth.transport.requests.Request()
    creds.refresh(request)
    return creds.token


def sign_jwt_with_iam(access_token: str, subject: str) -> str:
    now = int(time.time())
    claims = {
        "iss": SERVICE_ACCOUNT_EMAIL,
        "sub": subject,
        "scope": " ".join(SCOPES),
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


def exchange_jwt_for_token(signed_jwt: str) -> str:
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


def build_drive_service() -> Any:
    subject = env("DRIVE_SUBJECT_EMAIL", DEFAULT_SUBJECT)
    key_path = env("DRIVE_SA_KEY_PATH")

    if key_path and Path(key_path).exists():
        print(f"Auth mode: service account key + DWD ({key_path})")
        creds = service_account.Credentials.from_service_account_file(
            key_path,
            scopes=SCOPES,
        ).with_subject(subject)
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    print("Auth mode: keyless DWD via local ADC + IAMCredentials signJwt")
    adc_token = get_adc_token()
    signed_jwt = sign_jwt_with_iam(adc_token, subject)
    workspace_token = exchange_jwt_for_token(signed_jwt)
    creds = oauth_credentials.Credentials(token=workspace_token)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def get_start_page_token(service: Any, drive_id: str | None) -> str:
    params: dict[str, Any] = {"fields": "startPageToken"}
    if drive_id:
        params["driveId"] = drive_id
        params["supportsAllDrives"] = True
    response = service.changes().getStartPageToken(**params).execute()
    return response["startPageToken"]


def get_or_init_page_token(service: Any, state_path: Path, drive_id: str | None) -> tuple[str, bool]:
    state = load_state(state_path)
    token = state.get("page_token")
    if token:
        return token, False

    token = get_start_page_token(service, drive_id)
    save_state(
        state_path,
        {
            "page_token": token,
            "initialized_at": utc_now(),
            "note": "First run initializes token. Run again after changing test folder contents.",
        },
    )
    return token, True


def list_changes(service: Any, page_token: str, drive_id: str | None) -> tuple[list[dict[str, Any]], str | None]:
    changes: list[dict[str, Any]] = []
    token = page_token
    new_start_page_token: str | None = None

    while token:
        params: dict[str, Any] = {
            "pageToken": token,
            "spaces": "drive",
            "includeItemsFromAllDrives": True,
            "supportsAllDrives": True,
            "fields": (
                "nextPageToken,newStartPageToken,"
                "changes(fileId,removed,time,type,changeType,"
                "file(id,name,mimeType,parents,trashed,modifiedTime,webViewLink,driveId))"
            ),
            "pageSize": 1000,
        }
        if drive_id:
            params["driveId"] = drive_id

        response = service.changes().list(**params).execute()
        changes.extend(response.get("changes", []))
        new_start_page_token = response.get("newStartPageToken") or new_start_page_token
        token = response.get("nextPageToken")

    return changes, new_start_page_token


def list_folder_children(service: Any, folder_id: str, drive_id: str | None) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    page_token: str | None = None
    query = f"'{folder_id}' in parents and trashed = false"

    while True:
        params: dict[str, Any] = {
            "q": query,
            "spaces": "drive",
            "includeItemsFromAllDrives": True,
            "supportsAllDrives": True,
            "fields": "nextPageToken,files(id,name,mimeType,parents,trashed,modifiedTime,webViewLink,driveId)",
            "pageSize": 1000,
        }
        if drive_id:
            params["corpora"] = "drive"
            params["driveId"] = drive_id
        if page_token:
            params["pageToken"] = page_token

        response = service.files().list(**params).execute()
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return files


def filter_changes_to_folder(changes: list[dict[str, Any]], folder_id: str) -> list[dict[str, Any]]:
    """Keep changes where folder_id is a direct parent.

    This is a one-level filter. A production reconciler needs recursive parent walking
    or a folder tree cache for deep Vault/project trees.
    """
    filtered = []
    for change in changes:
        file_obj = change.get("file") or {}
        parents = file_obj.get("parents") or []
        if folder_id in parents:
            filtered.append(change)
    return filtered


def save_fixture(fixtures_dir: Path, payload: dict[str, Any]) -> Path:
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    safe_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = fixtures_dir / f"probe_{safe_ts}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main() -> None:
    folder_id = env("DRIVE_FOLDER_ID", DEFAULT_FOLDER_ID)
    drive_id = env("DRIVE_ID")
    state_path = Path(env("DRIVE_STATE_PATH", str(DEFAULT_STATE_PATH)) or str(DEFAULT_STATE_PATH))
    fixtures_dir = Path(env("DRIVE_FIXTURES_DIR", str(DEFAULT_FIXTURES_DIR)) or str(DEFAULT_FIXTURES_DIR))

    print("Building Drive API service")
    service = build_drive_service()

    print("Getting or initializing page token")
    page_token, initialized = get_or_init_page_token(service, state_path, drive_id)

    if initialized:
        changes: list[dict[str, Any]] = []
        folder_changes: list[dict[str, Any]] = []
        new_token = page_token
        print("Initialized page token. Make changes in the test folder and run again.")
    else:
        print("Listing Drive changes")
        changes, new_token = list_changes(service, page_token, drive_id)
        folder_changes = filter_changes_to_folder(changes, folder_id)
        if new_token:
            save_state(
                state_path,
                {
                    "page_token": new_token,
                    "updated_at": utc_now(),
                    "previous_page_token": page_token,
                },
            )

    print("Listing current folder children")
    folder_children = list_folder_children(service, folder_id, drive_id)

    payload = {
        "run_at": utc_now(),
        "project_id": PROJECT_ID,
        "folder_id": folder_id,
        "drive_id": drive_id,
        "state_path": str(state_path),
        "input_page_token": page_token,
        "output_page_token": new_token,
        "initialized": initialized,
        "counts": {
            "changes": len(changes),
            "folder_changes": len(folder_changes),
            "folder_children": len(folder_children),
        },
        "changes": changes,
        "folder_changes": folder_changes,
        "folder_children": folder_children,
    }

    fixture_path = save_fixture(fixtures_dir, payload)
    print(f"Saved fixture: {fixture_path}")
    print(json.dumps(payload["counts"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except HttpError as exc:
        print("Drive API HttpError")
        print(exc)
        raise
