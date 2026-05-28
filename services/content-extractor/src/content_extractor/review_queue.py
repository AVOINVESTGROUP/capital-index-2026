"""Controlled Firestore write boundary for review queue items."""

from __future__ import annotations

import hashlib
import json
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


def review_queue_enabled_from_env() -> bool:
    return os.environ.get("REVIEW_QUEUE_ENABLED", "false").lower() == "true"


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def review_item(extracted: dict[str, Any]) -> dict[str, Any]:
    material = _compact_json(
        {
            "file_id": extracted.get("file_id"),
            "source_decision_id": extracted.get("source_decision_id"),
            "reason": extracted.get("review_reason"),
        }
    )
    review_id = f"review_{_stable_hash(material)[:24]}"
    return {
        "schema_version": "capital.review_queue_item.v1",
        "review_id": review_id,
        "status": "open",
        "priority": "normal",
        "reason": extracted.get("review_reason") or "review_required",
        "source": "content-extractor",
        "source_collection": "extracted_text",
        "file_id": extracted.get("file_id"),
        "source_decision_id": extracted.get("source_decision_id"),
        "source_event_id": extracted.get("source_event_id"),
        "source_load_id": extracted.get("source_load_id"),
        "trace_id": extracted.get("trace_id"),
        "idempotency_key": extracted.get("idempotency_key"),
        "sensitivity_class": extracted.get("sensitivity_class"),
        "doc_title": extracted.get("doc_title"),
        "char_count": extracted.get("char_count"),
        "next_action": extracted.get("next_action"),
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }


def write_review_queue_batch(
    batch: dict[str, Any],
    *,
    client: FirestoreClient,
    review_queue_enabled: bool,
) -> dict[str, Any]:
    candidates = [item for item in batch.get("extracted_text") or [] if item.get("review_required")]
    review_ids = [review_item(item)["review_id"] for item in candidates]
    if not review_queue_enabled:
        return {
            "status": "disabled",
            "collection": "review_queue",
            "attempted": 0,
            "would_write": len(candidates),
            "review_ids": review_ids,
        }

    written_ids: list[str] = []
    collection = client.collection("review_queue")
    for extracted in candidates:
        item = review_item(extracted)
        collection.document(item["review_id"]).set(item, merge=True)
        written_ids.append(item["review_id"])

    return {
        "status": "written",
        "collection": "review_queue",
        "attempted": len(candidates),
        "written": len(written_ids),
        "review_ids": written_ids,
    }
