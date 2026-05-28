"""Controlled Firestore write boundary for Drive Governance recommendations."""

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


def write_governance_batch(
    batch: dict[str, Any],
    *,
    client: FirestoreClient,
    write_enabled: bool,
) -> dict[str, Any]:
    """Write cleanup recommendations and duplicate clusters when explicitly enabled."""

    cleanup_items = batch.get("cleanup_queue") or []
    duplicate_clusters = batch.get("file_duplicates") or []
    cleanup_ids = [item.get("cleanup_id") for item in cleanup_items]
    duplicate_ids = [item.get("cluster_id") for item in duplicate_clusters]

    if not write_enabled:
        return {
            "status": "disabled",
            "attempted": 0,
            "would_write_cleanup_queue": len(cleanup_items),
            "would_write_file_duplicates": len(duplicate_clusters),
            "cleanup_ids": cleanup_ids,
            "duplicate_cluster_ids": duplicate_ids,
        }

    cleanup_written = _write_collection(client, "cleanup_queue", cleanup_items, "cleanup_id")
    duplicates_written = _write_collection(client, "file_duplicates", duplicate_clusters, "cluster_id")

    return {
        "status": "written",
        "attempted": cleanup_written + duplicates_written,
        "written_cleanup_queue": cleanup_written,
        "written_file_duplicates": duplicates_written,
        "cleanup_ids": cleanup_ids,
        "duplicate_cluster_ids": duplicate_ids,
        "written_at": utc_now(),
    }


def _write_collection(
    client: FirestoreClient,
    collection_name: str,
    items: list[dict[str, Any]],
    id_field: str,
) -> int:
    collection = client.collection(collection_name)
    written = 0
    for item in items:
        document_id = item.get(id_field)
        if not document_id:
            raise ValueError(f"{collection_name}.{id_field} is required for Firestore write")
        collection.document(document_id).set(item, merge=True)
        written += 1
    return written


def firestore_client(project_id: str, database: str) -> FirestoreClient:
    """Create a Firestore client lazily so local tests do not require the package."""

    from google.cloud import firestore

    return firestore.Client(project=project_id, database=database)
