"""Drive Governance gate for entity extraction candidates."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

ALLOWED_SOURCE_STATUS = "active"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def source_gate(file_record: dict[str, Any] | None) -> dict[str, Any]:
    """Return the Drive Governance decision for a file before entity extraction."""

    record = file_record or {}
    source_status = record.get("source_status")
    index_eligible = record.get("index_eligible")
    human_block = record.get("human_block", False)

    reasons: list[str] = []
    if source_status != ALLOWED_SOURCE_STATUS:
        reasons.append("source_status_not_active")
    if index_eligible is not True:
        reasons.append("index_eligible_not_true")
    if human_block is True:
        reasons.append("human_block")

    return {
        "allowed": not reasons,
        "reason": "allowed" if not reasons else "blocked_by_drive_governance",
        "reasons": reasons,
        "source_status": source_status,
        "index_eligible": index_eligible,
        "human_block": human_block,
    }


def make_entity_extraction_candidate(
    extracted_text: dict[str, Any],
    file_record: dict[str, Any] | None,
    *,
    batch_ref: str,
    index: int,
) -> dict[str, Any]:
    """Create the first entity-extractor contract object without calling AI."""

    file_id = extracted_text.get("file_id")
    gate = source_gate(file_record)
    candidate_material = _compact_json(
        {
            "file_id": file_id,
            "source_decision_id": extracted_text.get("source_decision_id"),
            "source_status": gate["source_status"],
            "index_eligible": gate["index_eligible"],
        }
    )
    next_action = "extract_entities" if gate["allowed"] else "blocked"

    return {
        "schema_version": "capital.entity_extraction_candidate.v1",
        "candidate_id": f"entity_candidate_{_stable_hash(candidate_material)[:24]}",
        "file_id": file_id,
        "project_id": extracted_text.get("project_id") or (file_record or {}).get("project_id"),
        "source_registry_id": extracted_text.get("source_registry_id")
        or (file_record or {}).get("source_registry_id"),
        "source_decision_id": extracted_text.get("source_decision_id"),
        "source_extraction_plan_id": extracted_text.get("plan_id"),
        "raw_extracted_text_ref": f"{batch_ref}#/extracted_text/{index}",
        "created_at": _utc_now(),
        "char_count": extracted_text.get("char_count", 0),
        "sensitivity_class": extracted_text.get("sensitivity_class"),
        "source_status": gate["source_status"],
        "index_eligible": gate["index_eligible"],
        "human_block": gate["human_block"],
        "gate_allowed": gate["allowed"],
        "gate_reason": gate["reason"],
        "gate_reasons": gate["reasons"],
        "next_action": next_action,
    }


def build_entity_candidates(
    extracted_batch: dict[str, Any],
    file_records_by_id: dict[str, dict[str, Any]],
    *,
    batch_ref: str,
) -> dict[str, Any]:
    items = extracted_batch.get("extracted_text") or []
    candidates = [
        make_entity_extraction_candidate(
            item,
            file_records_by_id.get(item.get("file_id")),
            batch_ref=batch_ref,
            index=index,
        )
        for index, item in enumerate(items)
    ]

    return {
        "schema_version": "capital.entity_extraction_candidate_batch.v1",
        "source": "entity_extractor",
        "input_batch_ref": batch_ref,
        "run_at": _utc_now(),
        "counts": {
            "input_extracted_text": len(items),
            "candidates": len(candidates),
            "allowed": sum(1 for item in candidates if item["gate_allowed"]),
            "blocked": sum(1 for item in candidates if not item["gate_allowed"]),
        },
        "entity_extraction_candidates": candidates,
    }
