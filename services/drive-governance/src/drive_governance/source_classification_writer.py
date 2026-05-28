"""Firestore writer for source classification decisions."""

from __future__ import annotations

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

    def batch(self) -> Any:
        ...


def write_source_classification_batch(
    batch: dict[str, Any],
    *,
    client: FirestoreClient,
    write_enabled: bool,
) -> dict[str, Any]:
    decisions = batch.get("decisions") or []
    changed = [item for item in decisions if _changed(item)]
    if not write_enabled:
        return {
            "status": "disabled",
            "attempted": 0,
            "would_update": len(changed),
            "would_preserve": len(decisions) - len(changed),
        }

    firestore_batch = client.batch()
    for item in changed:
        file_ref = client.collection("files").document(item["file_id"])
        action_id = f"source_rule_{item['file_id'][:16]}_{item['rule_id']}"
        action_ref = client.collection("source_quality_actions").document(action_id)
        firestore_batch.set(
            file_ref,
            {
                "source_status": item["new_source_status"],
                "index_eligible": item["new_index_eligible"],
                "human_block": item["new_human_block"],
                "source_quality_updated_at": item["created_at"],
                "source_quality_updated_by": "source_classifier",
                "source_quality_note": f"auto rule: {item['rule_id']}",
                "source_classification_rule_id": item["rule_id"],
                "source_classification_confidence": item["confidence"],
            },
            merge=True,
        )
        firestore_batch.set(
            action_ref,
            {
                "schema_version": "capital.source_quality_action.v1",
                "action_id": action_id,
                "file_id": item["file_id"],
                "actor_id": "source_classifier",
                "actor_type": "automation",
                "action": "auto_classify",
                "previous_source_status": item["previous_source_status"],
                "new_source_status": item["new_source_status"],
                "previous_index_eligible": item["previous_index_eligible"],
                "new_index_eligible": item["new_index_eligible"],
                "previous_human_block": item["previous_human_block"],
                "new_human_block": item["new_human_block"],
                "drive_mutation": "none",
                "drive_mutation_allowed": False,
                "policy_snapshot_id": "source_classifier_rules_v2",
                "approval_decision_id": None,
                "note": f"auto rule: {item['rule_id']}; confidence={item['confidence']}",
                "created_at": item["created_at"],
            },
        )
    firestore_batch.commit()
    return {
        "status": "written",
        "updated": len(changed),
        "preserved": len(decisions) - len(changed),
        "file_ids": [item["file_id"] for item in changed],
    }


def _changed(item: dict[str, Any]) -> bool:
    return (
        item["previous_source_status"] != item["new_source_status"]
        or item["previous_index_eligible"] != item["new_index_eligible"]
        or item["previous_human_block"] != item["new_human_block"]
    )
