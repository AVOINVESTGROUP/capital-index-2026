"""Produce an extraction plan from a normalized event and a policy decision."""

from __future__ import annotations

import hashlib
import json
from typing import Any

TEXT_EXTRACTABLE_MIME_TYPES = frozenset({
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation",
    "application/pdf",
    "text/plain",
    "text/csv",
})


def _plan_id(file_id: str | None, sensitivity_class: str) -> str:
    material = json.dumps(
        {"file_id": file_id, "sensitivity_class": sensitivity_class},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"plan_{digest[:24]}"


def make_extraction_plan(
    event: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Return what to do with a file given a normalized event and policy decision."""

    file_id = event.get("file_id")
    mime_type = (event.get("file") or {}).get("mime_type")
    allowed = set(policy.get("allowed_actions") or [])
    sensitivity_class = policy.get("sensitivity_class", "UNCLASSIFIED_REVIEW_REQUIRED")

    can_read = policy.get("decision") == "allow" and "read_content" in allowed
    can_extract_text = can_read and mime_type in TEXT_EXTRACTABLE_MIME_TYPES
    embedding_allowed = "embed" in allowed
    vault_publish_allowed = "publish_to_vault" in allowed
    ai_context_allowed = "include_in_ai_context" in allowed

    if not can_read:
        next_action = "blocked"
    elif not can_extract_text:
        next_action = "review_required"
    else:
        next_action = "extract_text"

    return {
        "plan_id": _plan_id(file_id, sensitivity_class),
        "file_id": file_id,
        "sensitivity_class": sensitivity_class,
        "can_read_content": can_read,
        "can_extract_text": can_extract_text,
        "text_only": can_extract_text,
        "embedding_allowed": embedding_allowed,
        "vault_publish_allowed": vault_publish_allowed,
        "ai_context_allowed": ai_context_allowed,
        "next_action": next_action,
    }
