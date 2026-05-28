"""Controlled Firestore write boundary for normalized event batches."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Protocol


class DocumentRef(Protocol):
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


def event_document(event: dict[str, Any]) -> dict[str, Any]:
    """Build the Firestore /events document payload for one normalized event."""

    return {
        **event,
        "firestore_schema_version": "capital.events.v1",
        "write_source": "event-ingestor",
        "written_at": utc_now(),
    }


def write_event_batch(
    batch: dict[str, Any],
    *,
    client: FirestoreClient,
    write_enabled: bool,
) -> dict[str, Any]:
    """Write normalized events to Firestore when explicitly enabled.

    With write_enabled=False this returns a dry-run summary and performs no
    client calls. This is the default Cloud Run behavior.
    """

    events = batch.get("events") or []
    if not write_enabled:
        return {
            "status": "disabled",
            "collection": "events",
            "attempted": 0,
            "would_write": len(events),
            "event_ids": [event.get("event_id") for event in events],
        }

    written_ids: list[str] = []
    collection = client.collection("events")
    for event in events:
        event_id = event.get("event_id")
        if not event_id:
            raise ValueError("event_id is required for Firestore write")
        collection.document(event_id).set(event_document(event), merge=True)
        written_ids.append(event_id)

    return {
        "status": "written",
        "collection": "events",
        "attempted": len(events),
        "written": len(written_ids),
        "event_ids": written_ids,
    }


def firestore_client(project_id: str, database: str) -> FirestoreClient:
    """Create a Firestore client lazily so local tests do not require the package."""

    from google.cloud import firestore

    return firestore.Client(project=project_id, database=database)
