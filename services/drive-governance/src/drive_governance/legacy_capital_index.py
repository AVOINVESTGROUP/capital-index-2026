"""Legacy CAPITAL_INDEX_2026 CSV mapping helpers."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def load_legacy_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_file_record(row: dict[str, str], *, imported_at: str | None = None) -> dict[str, Any]:
    imported_at = imported_at or utc_now()
    source_quality = source_quality_from_action(row.get("action", ""))
    file_id = _clean(row.get("file_id"))
    file_name = _clean(row.get("file_name"))
    project = _clean(row.get("project")) or "UNCATEGORIZED"

    return {
        "schema_version": "capital.file_metadata.v1",
        "file_id": file_id,
        "name": file_name,
        "mime_type": _clean(row.get("mime_type")),
        "web_view_link": _clean(row.get("file_url")),
        "parents": [_clean(row.get("parent_folder_id"))] if _clean(row.get("parent_folder_id")) else [],
        "parent_folder_name": _clean(row.get("parent_folder_name")),
        "owner_email": _clean(row.get("owner")),
        "created_time": _legacy_date(row.get("created")),
        "modified_time": _legacy_date(row.get("modified")),
        "size_bytes": _int_or_none(row.get("size_bytes")),
        "project_id": normalize_project_id(project),
        "legacy_project_name": project,
        "source_registry_id": "legacy_capital_index_2026",
        "metadata_status": "legacy_index_loaded",
        "source_status": source_quality["source_status"],
        "index_eligible": source_quality["index_eligible"],
        "human_block": source_quality["human_block"],
        "source_quality_updated_at": imported_at,
        "source_quality_updated_by": "legacy_capital_index_importer",
        "source_quality_note": source_quality["note"],
        "legacy_capital_index": {
            "action": _clean(row.get("action")),
            "enrichment_status": _clean(row.get("enrichment_status")),
            "summary_50w": _clean(row.get("summary_50w")),
            "sub_topic": _clean(row.get("sub_topic")),
            "type": _clean(row.get("type")),
            "status": _clean(row.get("status")),
            "linked_projects": _split_projects(row.get("linked_projects")),
            "value_score": _int_or_none(row.get("value_score")),
            "imported_at": imported_at,
        },
    }


def build_source_quality_action(record: dict[str, Any], *, imported_at: str | None = None) -> dict[str, Any]:
    imported_at = imported_at or record.get("source_quality_updated_at") or utc_now()
    file_id = record["file_id"]
    return {
        "schema_version": "capital.source_quality_action.v1",
        "action_id": f"legacy_capital_index_{file_id[:24]}",
        "file_id": file_id,
        "actor_id": "legacy_capital_index_importer",
        "actor_type": "automation",
        "action": "import_legacy_source_quality",
        "previous_source_status": None,
        "new_source_status": record["source_status"],
        "previous_index_eligible": None,
        "new_index_eligible": record["index_eligible"],
        "previous_human_block": None,
        "new_human_block": record["human_block"],
        "drive_mutation": "none",
        "drive_mutation_allowed": False,
        "policy_snapshot_id": "legacy_capital_index_2026_import_v1",
        "approval_decision_id": None,
        "note": record["source_quality_note"],
        "created_at": imported_at,
    }


def summarize_records(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    records = list(records)
    return {
        "input_rows": len(records),
        "active": sum(1 for item in records if item["source_status"] == "active"),
        "needs_human_review": sum(1 for item in records if item["source_status"] == "needs_human_review"),
        "candidate_archive": sum(1 for item in records if item["source_status"] == "candidate_archive"),
        "index_eligible": sum(1 for item in records if item["index_eligible"] is True),
        "ai_done": sum(
            1 for item in records if item.get("legacy_capital_index", {}).get("enrichment_status") == "AI_DONE"
        ),
    }


def source_quality_from_action(action: str) -> dict[str, Any]:
    normalized = _clean(action).upper()
    if normalized == "KEEP":
        return {
            "source_status": "active",
            "index_eligible": True,
            "human_block": False,
            "note": "legacy CAPITAL_INDEX_2026 action KEEP",
        }
    if normalized == "DELETE":
        return {
            "source_status": "candidate_archive",
            "index_eligible": False,
            "human_block": False,
            "note": "legacy CAPITAL_INDEX_2026 action DELETE; deletion requires human approval",
        }
    if normalized == "REVIEW":
        return {
            "source_status": "needs_human_review",
            "index_eligible": False,
            "human_block": False,
            "note": "legacy CAPITAL_INDEX_2026 action REVIEW",
        }
    return {
        "source_status": "needs_human_review",
        "index_eligible": False,
        "human_block": False,
        "note": "legacy CAPITAL_INDEX_2026 action empty or unknown",
    }


def normalize_project_id(project_name: str) -> str:
    normalized = _clean(project_name).lower()
    replacements = {
        " ": "_",
        "-": "_",
        "/": "_",
        "\\": "_",
    }
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    normalized = "".join(ch for ch in normalized if ch.isalnum() or ch == "_")
    return normalized or "uncategorized"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _legacy_date(value: str | None) -> str | None:
    value = _clean(value)
    if not value:
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            pass
    return value


def _split_projects(value: str | None) -> list[str]:
    value = _clean(value)
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _int_or_none(value: str | None) -> int | None:
    value = _clean(value)
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _clean(value: str | None) -> str:
    return (value or "").strip()
