"""Build /files upsert payloads from normalized Drive events."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "capital.file_metadata_batch.v1"
PAYLOAD_SCHEMA_VERSION = "capital.file_metadata_upsert.v1"
SOURCE = "metadata_loader"
DEFAULT_NEXT_ACTION = "policy_check"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _review_reason(event: dict[str, Any]) -> str | None:
    if event.get("review_required"):
        return event.get("review_reason") or "upstream_review_required"
    if not event.get("file_id"):
        return "missing_file_id"
    if not event.get("project_id"):
        return "missing_project_id"
    if not event.get("source_registry_id"):
        return "missing_source_registry_id"
    return None


def build_file_upsert(event: dict[str, Any], *, batch_ref: str, index: int) -> dict[str, Any]:
    """Convert one normalized event into a /files/{file_id} upsert payload."""

    file_obj = event.get("file") or {}
    file_id = event.get("file_id") or file_obj.get("id")
    review_reason = _review_reason(event)
    load_material = _compact_json(
        {
            "event_id": event.get("event_id"),
            "file_id": file_id,
            "observed_at": event.get("observed_at"),
            "source_registry_id": event.get("source_registry_id"),
        }
    )
    load_id = f"metadata_{_stable_hash(load_material)[:24]}"

    return {
        "schema_version": PAYLOAD_SCHEMA_VERSION,
        "operation": "upsert",
        "load_id": load_id,
        "source": SOURCE,
        "source_event_id": event.get("event_id"),
        "trace_id": event.get("trace_id"),
        "idempotency_key": event.get("idempotency_key"),
        "raw_event_ref": f"{batch_ref}#/events/{index}",
        "loaded_at": _utc_now(),
        "metadata_status": "base_loaded",
        "authoritative_refetch_status": "pending",
        "next_action": DEFAULT_NEXT_ACTION if not review_reason else "review_required",
        "review_required": review_reason is not None,
        "review_reason": review_reason,
        "file": {
            "file_id": file_id,
            "name": file_obj.get("name"),
            "mime_type": file_obj.get("mime_type"),
            "parents": file_obj.get("parents") or [],
            "trashed": file_obj.get("trashed", False),
            "modified_time": file_obj.get("modified_time"),
            "web_view_link": file_obj.get("web_view_link"),
            "gcp_project_id": event.get("gcp_project_id"),
            "project_id": event.get("project_id"),
            "source_registry_id": event.get("source_registry_id"),
            "source": event.get("source"),
            "observed_at": event.get("observed_at"),
            "last_event_type": event.get("event_type"),
        },
        "authoritative_fields": {
            "owners": None,
            "head_revision_id": None,
            "drive_labels": None,
            "capabilities": None,
            "permissions_summary": None,
        },
    }


def load_metadata_batch(path: Path) -> dict[str, Any]:
    """Build metadata upsert payloads for every event in a normalized batch."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    events = payload.get("events") or []
    batch_ref = path.as_posix()
    upserts = [
        build_file_upsert(event, batch_ref=batch_ref, index=index)
        for index, event in enumerate(events)
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "source": SOURCE,
        "input_batch_ref": batch_ref,
        "run_at": _utc_now(),
        "gcp_project_id": payload.get("gcp_project_id"),
        "project_id": payload.get("project_id"),
        "source_registry_id": payload.get("source_registry_id"),
        "counts": {
            "input_events": len(events),
            "file_upserts": len(upserts),
            "review_required": sum(1 for item in upserts if item["review_required"]),
        },
        "file_upserts": upserts,
    }


def load_metadata_payload(payload: dict[str, Any], *, batch_ref: str) -> dict[str, Any]:
    """Build metadata upsert payloads from a normalized event batch object."""

    events = payload.get("events") or []
    upserts = [
        build_file_upsert(event, batch_ref=batch_ref, index=index)
        for index, event in enumerate(events)
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "source": SOURCE,
        "input_batch_ref": batch_ref,
        "run_at": _utc_now(),
        "gcp_project_id": payload.get("gcp_project_id"),
        "project_id": payload.get("project_id"),
        "source_registry_id": payload.get("source_registry_id"),
        "counts": {
            "input_events": len(events),
            "file_upserts": len(upserts),
            "review_required": sum(1 for item in upserts if item["review_required"]),
        },
        "file_upserts": upserts,
    }
