"""Controlled Firestore write boundary for file metadata upserts."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Protocol


class DocumentRef(Protocol):
    def get(self) -> Any:
        ...

    def set(self, data: dict[str, Any], merge: bool = False) -> Any:
        ...


class CollectionRef(Protocol):
    def document(self, document_id: str) -> DocumentRef:
        ...


class FirestoreClient(Protocol):
    def collection(self, collection_name: str) -> CollectionRef:
        ...


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_enabled_from_env() -> bool:
    return os.environ.get("WRITE_ENABLED", "false").lower() == "true"


def file_document(upsert: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the Firestore /files document payload for one metadata upsert."""

    file_payload = upsert.get("file") or {}
    existing_payload = existing or {}
    return {
        **file_payload,
        "firestore_schema_version": "capital.files.v1",
        "write_source": "metadata-loader",
        "last_metadata_load_id": upsert.get("load_id"),
        "last_source_event_id": upsert.get("source_event_id"),
        "last_idempotency_key": upsert.get("idempotency_key"),
        "metadata_status": upsert.get("metadata_status"),
        "authoritative_refetch_status": upsert.get("authoritative_refetch_status"),
        "authoritative_fields": upsert.get("authoritative_fields") or {},
        "source_status": file_payload.get("source_status")
        or existing_payload.get("source_status")
        or "needs_human_review",
        "index_eligible": _first_present(
            file_payload,
            existing_payload,
            "index_eligible",
            default=False,
        ),
        "human_block": _first_present(file_payload, existing_payload, "human_block", default=False),
        "review_required": upsert.get("review_required", False),
        "review_reason": upsert.get("review_reason"),
        "next_action": upsert.get("next_action"),
        "updated_at": utc_now(),
    }


def write_metadata_batch(
    batch: dict[str, Any],
    *,
    client: FirestoreClient,
    write_enabled: bool,
) -> dict[str, Any]:
    """Write file metadata to Firestore when explicitly enabled."""

    upserts = batch.get("file_upserts") or []
    file_ids = [(item.get("file") or {}).get("file_id") for item in upserts]
    if not write_enabled:
        return {
            "status": "disabled",
            "collection": "files",
            "attempted": 0,
            "would_write": len(upserts),
            "file_ids": file_ids,
        }

    written_ids: list[str] = []
    collection = client.collection("files")
    for upsert in upserts:
        file_id = (upsert.get("file") or {}).get("file_id")
        if not file_id:
            raise ValueError("file.file_id is required for Firestore write")
        document = collection.document(file_id)
        existing = _existing_document(document)
        document.set(file_document(upsert, existing), merge=True)
        written_ids.append(file_id)

    return {
        "status": "written",
        "collection": "files",
        "attempted": len(upserts),
        "written": len(written_ids),
        "file_ids": written_ids,
    }


def firestore_client(project_id: str, database: str) -> FirestoreClient:
    """Create a Firestore client lazily so local tests do not require the package."""

    from google.cloud import firestore

    return firestore.Client(project=project_id, database=database)


def _existing_document(document: DocumentRef) -> dict[str, Any]:
    try:
        snapshot = document.get()
    except AttributeError:
        return {}
    if not getattr(snapshot, "exists", True):
        return {}
    data = snapshot.to_dict()
    return data if isinstance(data, dict) else {}


def _first_present(
    first: dict[str, Any],
    second: dict[str, Any],
    key: str,
    *,
    default: Any,
) -> Any:
    if key in first:
        return first[key]
    if key in second:
        return second[key]
    return default
