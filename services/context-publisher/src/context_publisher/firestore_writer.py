"""Controlled Firestore write boundary for context publications."""

from __future__ import annotations

import os
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


def write_enabled_from_env() -> bool:
    return os.environ.get("WRITE_ENABLED", "false").lower() == "true"


def write_context_publication(
    publication: dict[str, Any],
    *,
    client: FirestoreClient,
    write_enabled: bool,
) -> dict[str, Any]:
    bundle = publication["bundle"]
    projection = publication["vault_projection"]
    counts = publication.get("counts") or {}
    if not write_enabled:
        return {
            "status": "disabled",
            "would_write": {
                "claims": counts.get("claims", 0),
                "source_evidence": counts.get("evidence", 0),
                "entities": counts.get("entities", 0),
                "relationships": counts.get("relationships", 0),
                "context_bundles": 2,
                "vault_projections": 1,
            },
            "bundle_id": bundle["bundle_id"],
        }

    _write_items(client, "source_evidence", publication.get("source_evidence") or [], "evidence_id")
    _write_items(client, "claims", publication.get("claims") or [], "claim_id")
    _write_items(client, "entities", publication.get("entities") or [], "entity_id")
    _write_items(client, "relationships", publication.get("relationships") or [], "relationship_id")
    client.collection("context_bundles").document(bundle["bundle_id"]).set(bundle, merge=True)
    client.collection("context_bundles").document("current").set(bundle, merge=True)
    client.collection("vault_projections").document(projection["projection_id"]).set(projection, merge=True)
    client.collection("vault_projections").document("current_second_brain").set(projection, merge=True)

    return {
        "status": "written",
        "bundle_id": bundle["bundle_id"],
        "projection_id": projection["projection_id"],
        "written": {
            "claims": counts.get("claims", 0),
            "source_evidence": counts.get("evidence", 0),
            "entities": counts.get("entities", 0),
            "relationships": counts.get("relationships", 0),
            "context_bundles": 2,
            "vault_projections": 2,
        },
    }


def firestore_client(project_id: str, database: str) -> FirestoreClient:
    from google.cloud import firestore

    return firestore.Client(project=project_id, database=database)


def _write_items(client: FirestoreClient, collection: str, items: list[dict[str, Any]], id_field: str) -> None:
    ref = client.collection(collection)
    for item in items:
        document_id = item.get(id_field)
        if not document_id:
            raise ValueError(f"{collection}.{id_field} is required")
        ref.document(document_id).set(item, merge=True)
