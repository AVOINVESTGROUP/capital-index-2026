"""Controlled Firestore write boundary for extracted text."""

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


def extracted_document(item: dict[str, Any]) -> dict[str, Any]:
    return {
        **item,
        "firestore_schema_version": "capital.extracted_text.v1",
        "write_source": "content-extractor",
        "written_at": utc_now(),
    }


def write_extracted_batch(
    batch: dict[str, Any],
    *,
    client: FirestoreClient,
    write_enabled: bool,
) -> dict[str, Any]:
    items = batch.get("extracted_text") or []
    file_ids = [item.get("file_id") for item in items]
    if not write_enabled:
        return {
            "status": "disabled",
            "collection": "extracted_text",
            "attempted": 0,
            "would_write": len(items),
            "file_ids": file_ids,
        }

    written_ids: list[str] = []
    collection = client.collection("extracted_text")
    for item in items:
        file_id = item.get("file_id")
        if not file_id:
            raise ValueError("file_id is required for Firestore write")
        collection.document(file_id).set(extracted_document(item), merge=True)
        written_ids.append(file_id)

    return {
        "status": "written",
        "collection": "extracted_text",
        "attempted": len(items),
        "written": len(written_ids),
        "file_ids": written_ids,
    }


def firestore_client(project_id: str, database: str) -> FirestoreClient:
    from google.cloud import firestore

    return firestore.Client(project=project_id, database=database)
