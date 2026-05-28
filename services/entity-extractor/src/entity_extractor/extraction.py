"""Entity extraction result builder behind the Drive Governance gate."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

MIN_ENTITY_CONFIDENCE = 0.5
MIN_RELATIONSHIP_CONFIDENCE = 0.75


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _entity_id(file_id: str, entity_type: str, name: str) -> str:
    material = _compact_json({"file_id": file_id, "type": entity_type, "name": name})
    return f"entity_{_stable_hash(material)[:24]}"


def _relationship_id(file_id: str, relationship: dict[str, Any]) -> str:
    material = _compact_json(
        {
            "file_id": file_id,
            "relationship_type": relationship.get("relationship_type"),
            "from_id": relationship.get("from_id"),
            "to_id": relationship.get("to_id"),
            "reason": relationship.get("reason"),
        }
    )
    return f"relationship_{_stable_hash(material)[:24]}"


def build_entity_extraction_result(
    candidate: dict[str, Any],
    extracted_text: dict[str, Any],
    ai_response: dict[str, Any] | None,
    *,
    provider_id: str,
    model_id: str,
    prompt_version: str = "entity-extractor.v1",
) -> dict[str, Any]:
    """Build a normalized entity extraction document from an AI JSON response.

    The function never extracts entities when the candidate is blocked by Drive Governance.
    """

    file_id = candidate.get("file_id") or extracted_text.get("file_id")
    extraction_material = _compact_json(
        {
            "candidate_id": candidate.get("candidate_id"),
            "file_id": file_id,
            "source_decision_id": candidate.get("source_decision_id"),
            "provider_id": provider_id,
            "model_id": model_id,
        }
    )

    if candidate.get("gate_allowed") is not True:
        return {
            "schema_version": "capital.extracted_entities.v1",
            "extraction_id": f"entity_extraction_{_stable_hash(extraction_material)[:24]}",
            "candidate_id": candidate.get("candidate_id"),
            "file_id": file_id,
            "project_id": candidate.get("project_id"),
            "source_registry_id": candidate.get("source_registry_id"),
            "source_decision_id": candidate.get("source_decision_id"),
            "source_extraction_plan_id": candidate.get("source_extraction_plan_id"),
            "provider_id": provider_id,
            "model_id": model_id,
            "prompt_version": prompt_version,
            "created_at": _utc_now(),
            "input_char_count": extracted_text.get("char_count", 0),
            "gate_allowed": False,
            "status": "blocked",
            "issues": candidate.get("gate_reasons") or ["blocked_by_drive_governance"],
            "entities": [],
            "relationships": [],
        }

    response = ai_response or {}
    issues: list[str] = []
    entities = _normalize_entities(file_id, response.get("entities") or [], issues)
    relationships = _normalize_relationships(file_id, response.get("relationships") or [], issues)
    status = "extracted" if entities or relationships else "needs_review"
    if status == "needs_review":
        issues.append("empty_ai_extraction")

    return {
        "schema_version": "capital.extracted_entities.v1",
        "extraction_id": f"entity_extraction_{_stable_hash(extraction_material)[:24]}",
        "candidate_id": candidate.get("candidate_id"),
        "file_id": file_id,
        "project_id": candidate.get("project_id"),
        "source_registry_id": candidate.get("source_registry_id"),
        "source_decision_id": candidate.get("source_decision_id"),
        "source_extraction_plan_id": candidate.get("source_extraction_plan_id"),
        "provider_id": provider_id,
        "model_id": model_id,
        "prompt_version": prompt_version,
        "created_at": _utc_now(),
        "input_char_count": extracted_text.get("char_count", 0),
        "gate_allowed": True,
        "status": status,
        "issues": issues,
        "entities": entities,
        "relationships": relationships,
    }


def build_entity_extraction_prompt(candidate: dict[str, Any], extracted_text: dict[str, Any]) -> dict[str, str]:
    """Create the provider-neutral prompt payload for an entity extraction model."""

    if candidate.get("gate_allowed") is not True:
        raise ValueError("Cannot build AI prompt for a blocked source")

    text = extracted_text.get("text") or ""
    return {
        "system": (
            "Extract business entities and relationships from approved CAPITAL INDEX source text. "
            "Return strict JSON only. Do not invent facts. Use evidence from the text."
        ),
        "user": json.dumps(
            {
                "file_id": candidate.get("file_id"),
                "project_id": candidate.get("project_id"),
                "sensitivity_class": candidate.get("sensitivity_class"),
                "output_schema": {
                    "entities": [
                        {
                            "type": "PROJECT|COMPANY|PERSON|ASSET|DOCUMENT|TASK|DATE|MONEY|LOCATION|OTHER",
                            "name": "string",
                            "confidence": "number 0..1",
                            "evidence_text": "short exact evidence",
                            "attributes": {},
                        }
                    ],
                    "relationships": [
                        {
                            "relationship_type": "string",
                            "from_id": "entity_id or name",
                            "to_id": "entity_id or name",
                            "confidence": "number 0..1, minimum 0.75",
                            "evidence_file_ids": ["file_id"],
                            "evidence_artifact_ids": ["candidate_id"],
                            "reason": "short explanation",
                        }
                    ],
                },
                "text": text,
            },
            ensure_ascii=False,
        ),
    }


def _normalize_entities(
    file_id: str,
    raw_entities: list[dict[str, Any]],
    issues: list[str],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_entities:
        name = str(raw.get("name") or "").strip()
        entity_type = str(raw.get("type") or "OTHER").strip().upper()
        confidence = _confidence(raw.get("confidence"))
        if not name:
            issues.append("dropped_entity_missing_name")
            continue
        if confidence < MIN_ENTITY_CONFIDENCE:
            issues.append("dropped_entity_low_confidence")
            continue
        entity_id = _entity_id(file_id, entity_type, name)
        if entity_id in seen:
            continue
        seen.add(entity_id)
        normalized.append(
            {
                "entity_id": entity_id,
                "type": entity_type,
                "name": name,
                "confidence": confidence,
                "evidence_text": str(raw.get("evidence_text") or "").strip(),
                "attributes": raw.get("attributes") if isinstance(raw.get("attributes"), dict) else {},
            }
        )
    return normalized


def _normalize_relationships(
    file_id: str,
    raw_relationships: list[dict[str, Any]],
    issues: list[str],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_relationships:
        relationship_type = str(raw.get("relationship_type") or "").strip()
        from_id = str(raw.get("from_id") or "").strip()
        to_id = str(raw.get("to_id") or "").strip()
        confidence = _confidence(raw.get("confidence"))
        if not relationship_type or not from_id or not to_id:
            issues.append("dropped_relationship_missing_endpoint")
            continue
        if confidence < MIN_RELATIONSHIP_CONFIDENCE:
            issues.append("dropped_relationship_low_confidence")
            continue
        relationship_id = _relationship_id(file_id, raw)
        if relationship_id in seen:
            continue
        seen.add(relationship_id)
        normalized.append(
            {
                "relationship_id": relationship_id,
                "relationship_type": relationship_type,
                "from_id": from_id,
                "to_id": to_id,
                "confidence": confidence,
                "evidence_file_ids": _string_list(raw.get("evidence_file_ids")),
                "evidence_artifact_ids": _string_list(raw.get("evidence_artifact_ids")),
                "reason": str(raw.get("reason") or "").strip(),
            }
        )
    return normalized


def _confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
