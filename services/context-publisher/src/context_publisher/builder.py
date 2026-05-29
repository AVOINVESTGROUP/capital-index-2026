"""Evidence-first context bundle builder for CAPITAL INDEX Second Brain."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

ACTIVE_STATUS = "active"
SCHEMA_VERSION = "capital.context_bundle.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_second_brain_publication(
    source: dict[str, Any],
    *,
    bundle_type: str = "second_brain",
    max_bundle_bytes: int = 120_000,
    created_by: str = "context-publisher",
) -> dict[str, Any]:
    """Build normalized memory artifacts and one bundle from approved Firestore state."""

    files_by_id = {
        item.get("file_id"): item
        for item in source.get("files", [])
        if item.get("file_id") and _file_is_context_allowed(item)
    }
    extracted_by_file_id = {
        item.get("file_id"): item
        for item in source.get("extracted_text", [])
        if item.get("file_id") in files_by_id and item.get("ai_context_allowed") is True
    }
    entity_extractions = [
        item
        for item in source.get("entity_extractions", [])
        if item.get("file_id") in files_by_id and item.get("status") == "extracted"
    ]

    evidence = _build_source_evidence(files_by_id, extracted_by_file_id)
    entities = _build_entities(entity_extractions, evidence)
    relationships = _build_relationships(entity_extractions, evidence)
    claims = _build_claims(extracted_by_file_id, entity_extractions, evidence, entities, relationships)
    bundle = _build_bundle(
        bundle_type=bundle_type,
        created_by=created_by,
        max_bundle_bytes=max_bundle_bytes,
        source=source,
        files_by_id=files_by_id,
        extracted_by_file_id=extracted_by_file_id,
        evidence=evidence,
        entities=entities,
        relationships=relationships,
        claims=claims,
    )
    projection = build_vault_projection(bundle, claims=claims, entities=entities, relationships=relationships)

    return {
        "schema_version": "capital.context_publication.v1",
        "created_at": bundle["created_at"],
        "created_by": created_by,
        "bundle": bundle,
        "claims": claims,
        "source_evidence": evidence,
        "entities": entities,
        "relationships": relationships,
        "vault_projection": projection,
        "counts": {
            "source_files": len(files_by_id),
            "extracted_text": len(extracted_by_file_id),
            "claims": len(claims),
            "evidence": len(evidence),
            "entities": len(entities),
            "relationships": len(relationships),
        },
    }


def build_vault_projection(
    bundle: dict[str, Any],
    *,
    claims: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
) -> dict[str, Any]:
    title = "CAPITAL INDEX Second Brain"
    lines = [
        "---",
        f"bundle_id: {bundle['bundle_id']}",
        f"bundle_type: {bundle['bundle_type']}",
        f"generated_at: {bundle['created_at']}",
        "manual_override: false",
        "---",
        "",
        "# CAPITAL INDEX Second Brain",
        "",
        "<!-- CAPITAL_INDEX:GENERATED_START -->",
        "",
        "## System Status",
        "",
        f"- Claims: {len(claims)}",
        f"- Entities: {len(entities)}",
        f"- Relationships: {len(relationships)}",
        f"- Source files: {len(bundle['source_file_ids'])}",
        "",
        "## High Confidence Claims",
        "",
    ]
    for claim in claims[:30]:
        lines.append(f"- {claim['text']} `confidence={claim['confidence']:.2f}`")
    lines.extend(
        [
            "",
            "## Relationship Graph",
            "",
        ]
    )
    for relationship in relationships[:30]:
        lines.append(
            f"- {relationship['from_id']} --{relationship['relationship_type']}--> "
            f"{relationship['to_id']} `confidence={relationship['confidence']:.2f}`"
        )
    lines.extend(
        [
            "",
            "<!-- CAPITAL_INDEX:GENERATED_END -->",
            "",
            "## Manual Notes",
            "",
            "Manual notes stay outside generated blocks.",
            "",
        ]
    )
    projection_id = f"vault_projection_{stable_hash({'bundle_id': bundle['bundle_id'], 'title': title})[:24]}"
    return {
        "schema_version": "capital.vault_projection.v1",
        "projection_id": projection_id,
        "bundle_id": bundle["bundle_id"],
        "path": "00_SECOND_BRAIN_INDEX.md",
        "title": title,
        "content": "\n".join(lines),
        "protected_blocks": ["CAPITAL_INDEX:GENERATED_START..CAPITAL_INDEX:GENERATED_END"],
        "manual_override_respected": True,
        "write_status": "preview",
        "requires_approval": True,
        "created_at": bundle["created_at"],
    }


def _file_is_context_allowed(file_record: dict[str, Any]) -> bool:
    return (
        file_record.get("source_status") == ACTIVE_STATUS
        and file_record.get("index_eligible") is True
        and file_record.get("human_block") is not True
    )


def _build_source_evidence(
    files_by_id: dict[str, dict[str, Any]],
    extracted_by_file_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for file_id, extracted in sorted(extracted_by_file_id.items()):
        file_record = files_by_id[file_id]
        evidence_id = f"evidence_{stable_hash({'file_id': file_id, 'plan_id': extracted.get('plan_id')})[:24]}"
        text = str(extracted.get("text") or "")
        evidence.append(
            {
                "schema_version": "capital.source_evidence.v1",
                "evidence_id": evidence_id,
                "file_id": file_id,
                "source_artifact_id": extracted.get("plan_id") or file_id,
                "drive_url": file_record.get("web_view_link"),
                "title": extracted.get("doc_title") or file_record.get("name") or file_id,
                "project_id": extracted.get("project_id") or file_record.get("project_id"),
                "char_count": extracted.get("char_count") or len(text),
                "snippet": text[:600],
                "ai_context_allowed": True,
                "source_status": file_record.get("source_status"),
                "index_eligible": file_record.get("index_eligible"),
                "created_at": utc_now(),
            }
        )
    return evidence


def _evidence_by_file(evidence: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["file_id"]: item for item in evidence}


def _build_entities(
    entity_extractions: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence_by_file = _evidence_by_file(evidence)
    by_id: dict[str, dict[str, Any]] = {}
    for extraction in entity_extractions:
        file_id = extraction.get("file_id")
        for entity in extraction.get("entities") or []:
            entity_id = entity.get("entity_id")
            if not entity_id or entity_id in by_id:
                continue
            by_id[entity_id] = {
                "schema_version": "capital.entity.v1",
                "entity_id": entity_id,
                "type": entity.get("type"),
                "name": entity.get("name"),
                "confidence": _confidence(entity.get("confidence")),
                "evidence_file_ids": [file_id] if file_id else [],
                "evidence_ids": [evidence_by_file[file_id]["evidence_id"]] if file_id in evidence_by_file else [],
                "evidence_text": entity.get("evidence_text"),
                "attributes": entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {},
                "review_status": "proposed",
                "created_at": utc_now(),
            }
    return list(by_id.values())


def _build_relationships(
    entity_extractions: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence_by_file = _evidence_by_file(evidence)
    by_id: dict[str, dict[str, Any]] = {}
    for extraction in entity_extractions:
        file_id = extraction.get("file_id")
        for relationship in extraction.get("relationships") or []:
            relationship_id = relationship.get("relationship_id")
            if not relationship_id or relationship_id in by_id:
                continue
            evidence_file_ids = _string_list(relationship.get("evidence_file_ids")) or ([file_id] if file_id else [])
            by_id[relationship_id] = {
                "schema_version": "capital.relationship.v1",
                "relationship_id": relationship_id,
                "relationship_type": relationship.get("relationship_type"),
                "from_id": relationship.get("from_id"),
                "to_id": relationship.get("to_id"),
                "confidence": _confidence(relationship.get("confidence")),
                "evidence_file_ids": evidence_file_ids,
                "evidence_artifact_ids": _string_list(relationship.get("evidence_artifact_ids")),
                "evidence_ids": [
                    evidence_by_file[item]["evidence_id"] for item in evidence_file_ids if item in evidence_by_file
                ],
                "reason": relationship.get("reason"),
                "review_status": "proposed",
                "created_at": utc_now(),
            }
    return list(by_id.values())


def _build_claims(
    extracted_by_file_id: dict[str, dict[str, Any]],
    entity_extractions: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence_by_file = _evidence_by_file(evidence)
    claims: list[dict[str, Any]] = []
    for file_id, extracted in sorted(extracted_by_file_id.items()):
        text = str(extracted.get("text") or "").strip()
        if not text:
            continue
        claim_text = _first_sentence(text) or f"Approved source has extracted text: {extracted.get('doc_title') or file_id}"
        claims.append(_claim("document_signal", claim_text, 0.55, file_id, evidence_by_file))

    for entity in entities:
        file_id = (entity.get("evidence_file_ids") or [""])[0]
        claims.append(
            _claim(
                "entity_signal",
                f"{entity.get('name')} is referenced as {entity.get('type')}.",
                entity.get("confidence", 0.0),
                file_id,
                evidence_by_file,
                linked_entity_ids=[entity.get("entity_id")],
            )
        )

    for relationship in relationships:
        file_id = (relationship.get("evidence_file_ids") or [""])[0]
        claims.append(
            _claim(
                "relationship_signal",
                f"{relationship.get('from_id')} has relationship {relationship.get('relationship_type')} with {relationship.get('to_id')}.",
                relationship.get("confidence", 0.0),
                file_id,
                evidence_by_file,
                linked_relationship_ids=[relationship.get("relationship_id")],
            )
        )
    return claims


def _claim(
    claim_type: str,
    text: str,
    confidence: float,
    file_id: str,
    evidence_by_file: dict[str, dict[str, Any]],
    *,
    linked_entity_ids: list[str | None] | None = None,
    linked_relationship_ids: list[str | None] | None = None,
) -> dict[str, Any]:
    evidence_id = evidence_by_file.get(file_id, {}).get("evidence_id")
    claim_id = f"claim_{stable_hash({'type': claim_type, 'text': text, 'file_id': file_id})[:24]}"
    return {
        "schema_version": "capital.claim.v1",
        "claim_id": claim_id,
        "claim_type": claim_type,
        "text": text,
        "confidence": _confidence(confidence),
        "review_status": "proposed",
        "source_file_ids": [file_id] if file_id else [],
        "evidence_ids": [evidence_id] if evidence_id else [],
        "linked_entity_ids": [item for item in linked_entity_ids or [] if item],
        "linked_relationship_ids": [item for item in linked_relationship_ids or [] if item],
        "created_by_agent": "context-publisher",
        "created_at": utc_now(),
    }


def _build_bundle(
    *,
    bundle_type: str,
    created_by: str,
    max_bundle_bytes: int,
    source: dict[str, Any],
    files_by_id: dict[str, dict[str, Any]],
    extracted_by_file_id: dict[str, dict[str, Any]],
    evidence: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    claims: list[dict[str, Any]],
) -> dict[str, Any]:
    created_at = utc_now()
    source_file_ids = sorted(files_by_id.keys())
    bundle_id = f"context_bundle_{stable_hash({'type': bundle_type, 'created_at': created_at, 'files': source_file_ids})[:24]}"
    owner_profile = source.get("owner_profile") or {}
    body = {
        "owner_profile": owner_profile,
        "source_file_ids": source_file_ids,
        "claim_ids": [item["claim_id"] for item in claims],
        "entity_ids": [item["entity_id"] for item in entities],
        "relationship_ids": [item["relationship_id"] for item in relationships],
        "evidence_ids": [item["evidence_id"] for item in evidence],
        "recent_claims": claims[:50],
        "relationship_graph": relationships[:50],
    }
    serialized = json.dumps(body, ensure_ascii=False, sort_keys=True)
    omitted = []
    if len(serialized.encode("utf-8")) > max_bundle_bytes:
        body["recent_claims"] = claims[:20]
        body["relationship_graph"] = relationships[:20]
        omitted.append("bundle_trimmed_to_budget")
    return {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": bundle_id,
        "bundle_type": bundle_type,
        "created_at": created_at,
        "created_by": created_by,
        "policy_snapshot_id": source.get("policy_snapshot_id"),
        "approval_status": "draft",
        "requires_human_approval": True,
        "approved_by": None,
        "approved_at": None,
        "max_bundle_bytes": max_bundle_bytes,
        "actual_bundle_bytes": len(json.dumps(body, ensure_ascii=False).encode("utf-8")),
        "source_file_ids": source_file_ids,
        "included_extracted_text_file_ids": sorted(extracted_by_file_id.keys()),
        "omitted_or_blocked_sources": omitted + _blocked_source_summaries(source),
        "body": body,
    }


def _blocked_source_summaries(source: dict[str, Any]) -> list[dict[str, Any]]:
    blocked = []
    for item in source.get("files", []):
        if item.get("file_id") and not _file_is_context_allowed(item):
            blocked.append(
                {
                    "file_id": item.get("file_id"),
                    "reason": item.get("source_status") or "not_active",
                    "index_eligible": item.get("index_eligible"),
                    "human_block": item.get("human_block"),
                }
            )
    return blocked[:200]


def _first_sentence(text: str) -> str:
    compact = " ".join(text.split())
    if not compact:
        return ""
    for delimiter in [". ", "\n", "! ", "? "]:
        if delimiter in compact:
            return compact.split(delimiter, 1)[0][:240]
    return compact[:240]


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
