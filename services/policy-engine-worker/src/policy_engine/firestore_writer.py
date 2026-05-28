"""Controlled Firestore write boundary for policy decisions."""

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


def policy_document(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        **decision,
        "firestore_schema_version": "capital.policy_decisions.v1",
        "write_source": "policy-engine-worker",
        "written_at": utc_now(),
    }


def write_policy_batch(
    batch: dict[str, Any],
    *,
    client: FirestoreClient,
    write_enabled: bool,
) -> dict[str, Any]:
    decisions = batch.get("policy_decisions") or []
    decision_ids = [decision.get("decision_id") for decision in decisions]
    if not write_enabled:
        return {
            "status": "disabled",
            "collection": "policy_decisions",
            "attempted": 0,
            "would_write": len(decisions),
            "decision_ids": decision_ids,
        }

    written_ids: list[str] = []
    collection = client.collection("policy_decisions")
    for decision in decisions:
        decision_id = decision.get("decision_id")
        if not decision_id:
            raise ValueError("decision_id is required for Firestore write")
        collection.document(decision_id).set(policy_document(decision), merge=True)
        written_ids.append(decision_id)

    return {
        "status": "written",
        "collection": "policy_decisions",
        "attempted": len(decisions),
        "written": len(written_ids),
        "decision_ids": written_ids,
    }


def firestore_client(project_id: str, database: str) -> FirestoreClient:
    from google.cloud import firestore

    return firestore.Client(project=project_id, database=database)
