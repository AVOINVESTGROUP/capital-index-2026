"""Google Drive metadata scanner for controlled reconciliation."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

SUPPORTED_FIELDS = (
    "nextPageToken,incompleteSearch,files(id,name,mimeType,parents,trashed,modifiedTime,createdTime,"
    "webViewLink,driveId,size)"
)
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def scan_drive(
    service: Any,
    *,
    root_folder_ids: list[str],
    max_files: int,
    include_folders: bool = False,
) -> dict[str, Any]:
    """Scan configured Drive roots and return a metadata inventory.

    The scanner does not mutate Drive and does not read file content.
    """

    seen_folders: set[str] = set()
    queued_folders = list(dict.fromkeys(root_folder_ids))
    files: list[dict[str, Any]] = []
    folders_seen = 0

    while queued_folders and len(files) < max_files:
        folder_id = queued_folders.pop(0)
        if folder_id in seen_folders:
            continue
        seen_folders.add(folder_id)
        folders_seen += 1
        for item in list_children(service, folder_id=folder_id):
            if item.get("mimeType") == FOLDER_MIME_TYPE:
                queued_folders.append(item["id"])
                if include_folders and len(files) < max_files:
                    files.append(item)
            elif len(files) < max_files:
                files.append(item)
            if len(files) >= max_files:
                break

    return {
        "schema_version": "capital.drive_scan_inventory.v1",
        "source": "drive_scanner",
        "run_at": utc_now(),
        "root_folder_ids": root_folder_ids,
        "counts": {
            "folders_seen": folders_seen,
            "files": len(files),
            "limit": max_files,
            "truncated": bool(queued_folders or len(files) >= max_files),
        },
        "files": files,
    }


def scan_all_drive_files(
    service: Any,
    *,
    max_files: int,
    include_folders: bool = False,
) -> dict[str, Any]:
    """Scan all visible Drive files through the metadata API.

    This mode is for production inventory refreshes. It does not recurse from a
    single root and still does not read file content.
    """

    files: list[dict[str, Any]] = []
    page_token = None
    pages_seen = 0
    incomplete_search = False

    while len(files) < max_files:
        response = (
            service.files()
            .list(
                q="trashed=false",
                corpora="allDrives",
                spaces="drive",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                pageSize=min(1000, max_files - len(files)),
                pageToken=page_token,
                fields=SUPPORTED_FIELDS,
            )
            .execute()
        )
        pages_seen += 1
        incomplete_search = incomplete_search or bool(response.get("incompleteSearch"))

        for item in response.get("files") or []:
            if item.get("mimeType") == FOLDER_MIME_TYPE and not include_folders:
                continue
            files.append(item)
            if len(files) >= max_files:
                break

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return {
        "schema_version": "capital.drive_scan_inventory.v1",
        "source": "drive_scanner",
        "scan_mode": "all_drive",
        "run_at": utc_now(),
        "root_folder_ids": [],
        "counts": {
            "pages_seen": pages_seen,
            "files": len(files),
            "limit": max_files,
            "truncated": bool(page_token or len(files) >= max_files),
            "incomplete_search": incomplete_search,
        },
        "files": files,
    }


def list_children(service: Any, *, folder_id: str) -> list[dict[str, Any]]:
    children: list[dict[str, Any]] = []
    page_token = None
    while True:
        response = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed=false",
                spaces="drive",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                pageSize=100,
                pageToken=page_token,
                fields=SUPPORTED_FIELDS,
            )
            .execute()
        )
        children.extend(response.get("files") or [])
        page_token = response.get("nextPageToken")
        if not page_token:
            return children


def inventory_to_normalized_events(
    inventory: dict[str, Any],
    *,
    gcp_project_id: str,
    project_id: str,
    source_registry_id: str,
) -> dict[str, Any]:
    observed_at = utc_now()
    events = [
        drive_file_to_event(
            item,
            index=index,
            observed_at=observed_at,
            gcp_project_id=gcp_project_id,
            project_id=project_id,
            source_registry_id=source_registry_id,
            batch_ref="drive_scan_inventory",
        )
        for index, item in enumerate(inventory.get("files") or [])
    ]
    return {
        "schema_version": "capital.normalized_drive_event_batch.v1",
        "source": "drive_scanner",
        "gcp_project_id": gcp_project_id,
        "project_id": project_id,
        "source_registry_id": source_registry_id,
        "events": events,
    }


def drive_file_to_event(
    file_obj: dict[str, Any],
    *,
    index: int,
    observed_at: str,
    gcp_project_id: str,
    project_id: str,
    source_registry_id: str,
    batch_ref: str,
) -> dict[str, Any]:
    file_id = file_obj["id"]
    event_material = f"{batch_ref}:{file_id}:{file_obj.get('modifiedTime') or ''}"
    event_hash = hashlib.sha256(event_material.encode("utf-8")).hexdigest()[:24]
    return {
        "schema_version": "capital.normalized_drive_event.v1",
        "event_id": f"evt_scan_{event_hash}",
        "event_type": "drive.file.changed",
        "source": "drive_scanner",
        "gcp_project_id": gcp_project_id,
        "project_id": project_id,
        "source_registry_id": source_registry_id,
        "file_id": file_id,
        "trace_id": f"trace_drive_scan_{event_hash}",
        "idempotency_key": f"drive_scan:{file_id}:{file_obj.get('modifiedTime') or ''}",
        "observed_at": observed_at,
        "raw_payload_ref": f"{batch_ref}#/files/{index}",
        "review_required": False,
        "review_reason": None,
        "file": {
            "id": file_id,
            "name": file_obj.get("name"),
            "mime_type": file_obj.get("mimeType"),
            "parents": file_obj.get("parents") or [],
            "trashed": file_obj.get("trashed", False),
            "modified_time": file_obj.get("modifiedTime"),
            "web_view_link": file_obj.get("webViewLink"),
        },
    }
