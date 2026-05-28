"""Controlled Firestore write boundary for entity extraction results."""

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


def entity_extraction_document(item: dict[str, Any]) -> dict[str, Any]:
    return {
        **item,
        "firestore_schema_version": "capital.extracted_entities.v1",
        "write_source": "entity-extractor",
        "written_at": utc_now(),
    }


def write_entity_extraction_batch(
    batch: dict[str, Any],
    *,
    client: FirestoreClient,
    write_enabled: bool,
) -> dict[str, Any]:
    items = batch.get("entity_extractions") or []
    extraction_ids = [item.get("extraction_id") for item in items]
    if not write_enabled:
        return {
            "status": "disabled",
            "collection": "entity_extractions",
            "attempted": 0,
            "would_write": len(items),
            "extraction_ids": extraction_ids,
        }

    collection = client.collection("entity_extractions")
    written_ids: list[str] = []
    for item in items:
        extraction_id = item.get("extraction_id")
        if not extraction_id:
            raise ValueError("extraction_id is required for Firestore write")
        collection.document(extraction_id).set(entity_extraction_document(item), merge=True)
        written_ids.append(extraction_id)

    return {
        "status": "written",
        "collection": "entity_extractions",
        "attempted": len(items),
        "written": len(written_ids),
        "extraction_ids": written_ids,
        "written_at": utc_now(),
    }


def firestore_client(project_id: str, database: str) -> FirestoreClient:
    from google.cloud import firestore

    return firestore.Client(project=project_id, database=database)
