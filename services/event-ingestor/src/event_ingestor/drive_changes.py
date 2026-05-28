"""Normalize Drive Changes API probe payloads into CAPITAL INDEX events."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE = "drive_changes"
DEFAULT_NEXT_ACTION = "load_metadata"
DEFAULT_PROJECT_ID = "capital_index"
DEFAULT_SOURCE_REGISTRY_ID = "drive_event_test"


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _event_type(change: dict[str, Any]) -> str:
    file_obj = change.get("file") or {}
    if change.get("removed") or file_obj.get("trashed"):
        return "drive.file.removed"
    return "drive.file.changed"


def _review_reason(change: dict[str, Any], folder_id: str | None) -> str | None:
    file_obj = change.get("file") or {}
    parents = file_obj.get("parents") or []

    if not file_obj:
        return "missing_file_metadata"
    if folder_id and folder_id not in parents:
        return "outside_probe_folder"
    if not file_obj.get("id") and not change.get("fileId"):
        return "missing_file_id"
    return None


def normalize_drive_change(
    change: dict[str, Any],
    *,
    fixture_path: str,
    fixture_run_at: str | None,
    gcp_project_id: str,
    project_id: str,
    source_registry_id: str,
    folder_id: str | None,
    input_page_token: str | None,
    output_page_token: str | None,
    index: int,
) -> dict[str, Any]:
    """Convert one Drive change into a normalized internal event."""

    file_obj = change.get("file") or {}
    file_id = change.get("fileId") or file_obj.get("id")
    observed_at = change.get("time") or fixture_run_at or _utc_now()
    source_event_type = change.get("changeType") or change.get("type") or "unknown"
    raw_ref = f"{fixture_path}#/folder_changes/{index}"

    idempotency_material = _compact_json(
        {
            "source": SOURCE,
            "gcp_project_id": gcp_project_id,
            "project_id": project_id,
            "source_registry_id": source_registry_id,
            "file_id": file_id,
            "time": observed_at,
            "removed": change.get("removed", False),
            "input_page_token": input_page_token,
            "output_page_token": output_page_token,
        }
    )
    idempotency_key = _stable_hash(idempotency_material)
    review_reason = _review_reason(change, folder_id)

    return {
        "event_id": f"evt_{idempotency_key[:24]}",
        "trace_id": f"trace_{idempotency_key[:24]}",
        "idempotency_key": idempotency_key,
        "source": SOURCE,
        "source_registry_id": source_registry_id,
        "source_event_type": source_event_type,
        "event_type": _event_type(change),
        "observed_at": observed_at,
        "gcp_project_id": gcp_project_id,
        "project_id": project_id,
        "file_id": file_id,
        "file": {
            "id": file_id,
            "name": file_obj.get("name"),
            "mime_type": file_obj.get("mimeType"),
            "parents": file_obj.get("parents") or [],
            "trashed": file_obj.get("trashed", False),
            "modified_time": file_obj.get("modifiedTime"),
            "web_view_link": file_obj.get("webViewLink"),
        },
        "drive": {
            "folder_id": folder_id,
            "input_page_token": input_page_token,
            "output_page_token": output_page_token,
        },
        "raw_payload_ref": raw_ref,
        "next_action": DEFAULT_NEXT_ACTION if not review_reason else "review_required",
        "review_required": review_reason is not None,
        "review_reason": review_reason,
    }


def normalize_probe_fixture(path: Path) -> dict[str, Any]:
    """Normalize all folder-scoped changes from one probe fixture."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    return normalize_probe_payload(payload, fixture_ref=path.as_posix())


def normalize_probe_payload(payload: dict[str, Any], *, fixture_ref: str) -> dict[str, Any]:
    """Normalize all folder-scoped changes from one Drive probe payload."""

    changes = payload.get("folder_changes") or []
    gcp_project_id = payload.get("project_id") or "unknown_gcp_project"
    project_id = payload.get("capital_project_id") or DEFAULT_PROJECT_ID
    source_registry_id = payload.get("source_registry_id") or DEFAULT_SOURCE_REGISTRY_ID
    folder_id = payload.get("folder_id")

    events = [
        normalize_drive_change(
            change,
            fixture_path=fixture_ref,
            fixture_run_at=payload.get("run_at"),
            gcp_project_id=gcp_project_id,
            project_id=project_id,
            source_registry_id=source_registry_id,
            folder_id=folder_id,
            input_page_token=payload.get("input_page_token"),
            output_page_token=payload.get("output_page_token"),
            index=index,
        )
        for index, change in enumerate(changes)
    ]

    return {
        "schema_version": "capital.event_batch.v1",
        "source": SOURCE,
        "fixture_path": fixture_ref,
        "run_at": payload.get("run_at"),
        "gcp_project_id": gcp_project_id,
        "project_id": project_id,
        "source_registry_id": source_registry_id,
        "folder_id": folder_id,
        "counts": {
            "input_changes": len(payload.get("changes") or []),
            "folder_changes": len(changes),
            "events": len(events),
            "review_required": sum(1 for event in events if event["review_required"]),
        },
        "events": events,
    }
