from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from google.cloud import firestore

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "drive-governance" / "src"))

from drive_governance.source_classifier import classify_batch  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply rules-based source classification to /files.")
    parser.add_argument("--project", default="capital-index-2026")
    parser.add_argument("--database", default="(default)")
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    db = firestore.Client(project=args.project, database=args.database)
    files = _files(db, args.limit)
    result = classify_batch(files)
    write_result = _write_decisions(db, result["decisions"]) if args.write else _dry_write(result["decisions"])

    print(
        json.dumps(
            {
                "write_enabled": args.write,
                "counts": result["counts"],
                "write": write_result,
                "sample": [
                    {
                        "file_id": item["file_id"],
                        "name": item["name"],
                        "from": item["previous_source_status"],
                        "to": item["new_source_status"],
                        "eligible": item["new_index_eligible"],
                        "rule": item["rule_id"],
                    }
                    for item in result["decisions"][:20]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _files(db: firestore.Client, limit: int) -> list[dict[str, Any]]:
    docs = db.collection("files").limit(limit).stream(timeout=60)
    return [doc.to_dict() | {"file_id": doc.to_dict().get("file_id") or doc.id} for doc in docs]


def _dry_write(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    changed = [item for item in decisions if _changed(item)]
    return {
        "status": "disabled",
        "attempted": 0,
        "would_update": len(changed),
        "would_preserve": len(decisions) - len(changed),
    }


def _write_decisions(db: firestore.Client, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    batch = db.batch()
    changed = [item for item in decisions if _changed(item)]
    for item in changed:
        file_ref = db.collection("files").document(item["file_id"])
        action_id = f"source_rule_{item['file_id'][:16]}_{item['rule_id']}"
        action_ref = db.collection("source_quality_actions").document(action_id)
        batch.set(
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
        batch.set(
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
                "policy_snapshot_id": "source_classifier_rules_v1",
                "approval_decision_id": None,
                "note": f"auto rule: {item['rule_id']}; confidence={item['confidence']}",
                "created_at": item["created_at"],
            },
        )
    batch.commit()
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


if __name__ == "__main__":
    raise SystemExit(main())
