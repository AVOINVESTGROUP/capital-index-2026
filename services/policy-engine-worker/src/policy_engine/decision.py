"""Apply local baseline policies to file metadata payloads."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "capital.policy_decision_batch.v1"
DECISION_SCHEMA_VERSION = "capital.policy_decision.v1"
SOURCE = "policy_engine_worker"

LOCAL_SOURCE_POLICIES: dict[str, dict[str, Any]] = {
    "drive_event_test": {
        "policy_id": "folder_policies/drive_event_test",
        "policy_name": "Drive Events POC Test Folder",
        "sensitivity_class": "PUBLIC_INTERNAL",
        "allowed_actions": ["read_metadata", "read_content"],
        "denied_actions": ["embed", "publish_to_vault", "include_in_ai_context"],
        "approval_required_for": [],
    },
    "vault_root": {
        "policy_id": "folder_policies/vault_root",
        "policy_name": "Vault Root Baseline",
        "sensitivity_class": "BUSINESS_CONFIDENTIAL",
        "allowed_actions": ["read_metadata", "read_content", "summarize", "embed"],
        "denied_actions": ["publish_restricted_context"],
        "approval_required_for": [],
    },
}

DEFAULT_LOCKED_POLICY = {
    "policy_id": "security_policies/default_locked",
    "policy_name": "Default Locked",
    "sensitivity_class": "UNCLASSIFIED_REVIEW_REQUIRED",
    "allowed_actions": ["read_metadata"],
    "denied_actions": [
        "read_content",
        "summarize",
        "embed",
        "publish_to_vault",
        "include_in_ai_context",
    ],
    "approval_required_for": ["read_content", "summary", "embedding", "context_publish"],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _policy_for(source_registry_id: str | None) -> tuple[dict[str, Any], bool]:
    if source_registry_id and source_registry_id in LOCAL_SOURCE_POLICIES:
        return LOCAL_SOURCE_POLICIES[source_registry_id], False
    return DEFAULT_LOCKED_POLICY, True


def _review_reason(upsert: dict[str, Any], unknown_policy: bool) -> str | None:
    if upsert.get("review_required"):
        return upsert.get("review_reason") or "upstream_review_required"
    if unknown_policy:
        return "unknown_source_registry"
    return None


def decide_file_policy(upsert: dict[str, Any], *, batch_ref: str, index: int) -> dict[str, Any]:
    """Build one policy decision from a metadata upsert payload."""

    file_payload = upsert.get("file") or {}
    source_registry_id = file_payload.get("source_registry_id")
    policy, unknown_policy = _policy_for(source_registry_id)
    review_reason = _review_reason(upsert, unknown_policy)
    decision_material = _compact_json(
        {
            "load_id": upsert.get("load_id"),
            "file_id": file_payload.get("file_id"),
            "source_registry_id": source_registry_id,
            "policy_id": policy["policy_id"],
        }
    )
    decision_id = f"policy_{_stable_hash(decision_material)[:24]}"

    return {
        "schema_version": DECISION_SCHEMA_VERSION,
        "decision_id": decision_id,
        "source": SOURCE,
        "source_load_id": upsert.get("load_id"),
        "source_event_id": upsert.get("source_event_id"),
        "trace_id": upsert.get("trace_id"),
        "idempotency_key": upsert.get("idempotency_key"),
        "raw_metadata_ref": f"{batch_ref}#/file_upserts/{index}",
        "decided_at": _utc_now(),
        "policy_snapshot_id": "local_seed_baseline_v1",
        "policy_id": policy["policy_id"],
        "policy_name": policy["policy_name"],
        "gcp_project_id": file_payload.get("gcp_project_id"),
        "project_id": file_payload.get("project_id"),
        "source_registry_id": source_registry_id,
        "file_id": file_payload.get("file_id"),
        "name": file_payload.get("name"),
        "mime_type": file_payload.get("mime_type"),
        "web_view_link": file_payload.get("web_view_link"),
        "sensitivity_class": policy["sensitivity_class"],
        "allowed_actions": policy["allowed_actions"],
        "denied_actions": policy["denied_actions"],
        "approval_required_for": policy["approval_required_for"],
        "review_required": review_reason is not None,
        "review_reason": review_reason,
        "next_action": "content_extraction_candidate" if not review_reason else "review_required",
    }


def apply_policy_batch(path: Path) -> dict[str, Any]:
    """Apply local policy decisions to every file upsert in a metadata batch."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    upserts = payload.get("file_upserts") or []
    batch_ref = path.as_posix()
    decisions = [
        decide_file_policy(upsert, batch_ref=batch_ref, index=index)
        for index, upsert in enumerate(upserts)
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "source": SOURCE,
        "input_batch_ref": batch_ref,
        "run_at": _utc_now(),
        "gcp_project_id": payload.get("gcp_project_id"),
        "project_id": payload.get("project_id"),
        "source_registry_id": payload.get("source_registry_id"),
        "counts": {
            "input_file_upserts": len(upserts),
            "policy_decisions": len(decisions),
            "review_required": sum(1 for decision in decisions if decision["review_required"]),
        },
        "policy_decisions": decisions,
    }


def apply_policy_payload(payload: dict[str, Any], *, batch_ref: str) -> dict[str, Any]:
    """Apply local policy decisions to a metadata batch object."""

    upserts = payload.get("file_upserts") or []
    decisions = [
        decide_file_policy(upsert, batch_ref=batch_ref, index=index)
        for index, upsert in enumerate(upserts)
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "source": SOURCE,
        "input_batch_ref": batch_ref,
        "run_at": _utc_now(),
        "gcp_project_id": payload.get("gcp_project_id"),
        "project_id": payload.get("project_id"),
        "source_registry_id": payload.get("source_registry_id"),
        "counts": {
            "input_file_upserts": len(upserts),
            "policy_decisions": len(decisions),
            "review_required": sum(1 for decision in decisions if decision["review_required"]),
        },
        "policy_decisions": decisions,
    }
