"""Firestore inventory reader for context publication."""

from __future__ import annotations

from typing import Any, Protocol


class CollectionRef(Protocol):
    def stream(self) -> Any:
        ...

    def limit(self, count: int) -> "CollectionRef":
        ...


class FirestoreClient(Protocol):
    def collection(self, collection_name: str) -> CollectionRef:
        ...


def build_context_source_from_firestore(
    *,
    client: FirestoreClient,
    limit: int,
    owner_profile: dict[str, Any] | None = None,
    policy_snapshot_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "capital.context_source.v1",
        "owner_profile": owner_profile or {},
        "policy_snapshot_id": policy_snapshot_id,
        "files": _collection(client, "files", limit),
        "extracted_text": _collection(client, "extracted_text", limit),
        "entity_extractions": _collection(client, "entity_extractions", limit),
        "review_queue": _collection(client, "review_queue", limit),
        "cleanup_queue": _collection(client, "cleanup_queue", limit),
    }


def _collection(client: FirestoreClient, name: str, limit: int) -> list[dict[str, Any]]:
    docs = client.collection(name).limit(limit).stream()
    items: list[dict[str, Any]] = []
    for doc in docs:
        data = doc.to_dict()
        if isinstance(data, dict):
            items.append(data)
    return items
