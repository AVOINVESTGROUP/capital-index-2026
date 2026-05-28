"""Build Drive Governance cleanup recommendations from file inventory fixtures."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

SCHEMA_VERSION = "capital.drive_governance_batch.v1"
POLICY_SNAPSHOT_ID = "policy_snapshot_governance_mvp"
RUN_AT = "2026-05-27T00:00:00Z"

COPY_PATTERN = re.compile(r"\b(copy|копия)\b", re.IGNORECASE)
DRAFT_PATTERN = re.compile(r"\b(draft|черновик|v\d+)\b", re.IGNORECASE)
FINAL_PATTERN = re.compile(r"\b(final|signed|подписан|signed final)\b", re.IGNORECASE)
TEMPORARY_PATTERN = re.compile(r"\b(tmp|temp|untitled|scan|img_\d+)\b", re.IGNORECASE)


def evaluate_inventory(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a Drive inventory payload and return governance recommendations."""

    files = payload.get("files") or []
    duplicate_clusters = _duplicate_clusters(files)
    cleanup_items = _cleanup_items(files, duplicate_clusters)

    return {
        "schema_version": SCHEMA_VERSION,
        "fixture_id": payload.get("fixture_id"),
        "generated_at": RUN_AT,
        "counts": {
            "input_files": len(files),
            "cleanup_queue": len(cleanup_items),
            "file_duplicates": len(duplicate_clusters),
        },
        "cleanup_queue": cleanup_items,
        "file_duplicates": duplicate_clusters,
    }


def _cleanup_items(
    files: list[dict[str, Any]],
    duplicate_clusters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    duplicate_member_to_canonical = _duplicate_member_to_canonical(duplicate_clusters)

    for file_obj in files:
        file_id = file_obj.get("file_id")
        if not file_id:
            continue
        if _is_empty(file_obj):
            items.append(_cleanup_item(file_obj, "candidate_empty", "empty", "needs_review", 0.98))
            continue
        if file_id in duplicate_member_to_canonical:
            canonical_id = duplicate_member_to_canonical[file_id]
            items.append(
                _cleanup_item(
                    file_obj,
                    "candidate_duplicate",
                    "duplicate",
                    "mark_duplicate",
                    0.99,
                    matched_file_ids=[canonical_id],
                    signals=["same_text_hash", "same_size", "copy_name_pattern", "same_parent"],
                    name_similarity=_name_similarity(file_obj.get("name"), _file_by_id(files, canonical_id).get("name")),
                    text_similarity=1.0,
                    details={"canonical_candidate_file_id": canonical_id},
                )
            )
            continue
        stale_match = _stale_match(file_obj, files)
        if stale_match:
            items.append(
                _cleanup_item(
                    file_obj,
                    "candidate_stale",
                    "version_superseded",
                    "archive",
                    0.86,
                    matched_file_ids=[stale_match["file_id"]],
                    signals=["draft_name_pattern", "older_version_pattern", "newer_final_in_same_parent"],
                    name_similarity=_name_similarity(file_obj.get("name"), stale_match.get("name")),
                    text_similarity=None,
                    details={"newer_final_file_id": stale_match["file_id"]},
                )
            )
            continue
        if not file_obj.get("project_id") or not file_obj.get("source_registry_id"):
            signals = []
            if not file_obj.get("project_id"):
                signals.append("missing_project_id")
            if not file_obj.get("source_registry_id"):
                signals.append("missing_source_registry_id")
            signals.append("unmapped_parent")
            items.append(
                _cleanup_item(
                    file_obj,
                    "needs_human_review",
                    "unknown_project",
                    "move_to_review",
                    0.9,
                    signals=signals,
                    details={"parents": file_obj.get("parents") or []},
                )
            )

    return [_with_cleanup_id(item, index + 1) for index, item in enumerate(items)]


def _duplicate_clusters(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, int | None, str | None], list[dict[str, Any]]] = {}
    for file_obj in files:
        text_hash = (file_obj.get("text_stats") or {}).get("text_hash")
        size = file_obj.get("size")
        parent = (file_obj.get("parents") or [None])[0]
        if not text_hash or size is None:
            continue
        groups.setdefault((text_hash, size, parent), []).append(file_obj)

    clusters: list[dict[str, Any]] = []
    for group in groups.values():
        if len(group) < 2:
            continue
        canonical = _canonical_file(group)
        member_ids = [item["file_id"] for item in group]
        other_names = [item for item in group if item["file_id"] != canonical["file_id"]]
        compared = other_names[0] if other_names else canonical
        clusters.append(
            {
                "schema_version": "capital.file_duplicate.v1",
                "cluster_id": _prefixed_id("dup", len(clusters) + 1),
                "cluster_type": "exact_duplicate",
                "canonical_file_id": canonical["file_id"],
                "member_file_ids": member_ids,
                "confidence": 0.99,
                "evidence": {
                    "signals": ["same_text_hash", "same_size", "same_parent", "copy_name_pattern"],
                    "name_similarity": _name_similarity(canonical.get("name"), compared.get("name")),
                    "text_similarity": 1.0,
                    "hash_match": True,
                    "same_parent": True,
                    "newest_file_id": _newest_file(group)["file_id"],
                    "details": {"canonical_reason": "non_copy_name_preferred"},
                },
                "action": "review_required",
                "created_at": RUN_AT,
                "updated_at": RUN_AT,
            }
        )
    return clusters


def _cleanup_item(
    file_obj: dict[str, Any],
    source_status: str,
    reason: str,
    recommended_action: str,
    confidence: float,
    *,
    matched_file_ids: list[str] | None = None,
    signals: list[str] | None = None,
    name_similarity: float | None = None,
    text_similarity: float | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text_stats = file_obj.get("text_stats") or {}
    return {
        "schema_version": "capital.cleanup_queue.v1",
        "cleanup_id": "",
        "file_id": file_obj["file_id"],
        "project_id": file_obj.get("project_id"),
        "source_registry_id": file_obj.get("source_registry_id"),
        "source_status": source_status,
        "reason": reason,
        "recommended_action": recommended_action,
        "confidence": confidence,
        "evidence": {
            "signals": signals or _default_signals(reason),
            "matched_file_ids": matched_file_ids or [],
            "name_similarity": name_similarity,
            "text_similarity": text_similarity,
            "age_days": _age_days(file_obj.get("modified_time")),
            "modified_at": file_obj.get("modified_time"),
            "size": file_obj.get("size"),
            "details": details
            if details is not None
            else {
                "char_count": text_stats.get("char_count"),
                "non_whitespace_char_count": text_stats.get("non_whitespace_char_count"),
            },
        },
        "policy_snapshot_id": POLICY_SNAPSHOT_ID,
        "human_approval_required": True,
        "status": "open",
        "created_at": RUN_AT,
        "resolved_at": None,
        "resolved_by": None,
    }


def _with_cleanup_id(item: dict[str, Any], index: int) -> dict[str, Any]:
    return {**item, "cleanup_id": _prefixed_id("cleanup", index)}


def _prefixed_id(prefix: str, index: int) -> str:
    return f"{prefix}_{index:024x}"


def _duplicate_member_to_canonical(clusters: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for cluster in clusters:
        canonical = cluster["canonical_file_id"]
        for member_id in cluster["member_file_ids"]:
            if member_id != canonical:
                result[member_id] = canonical
    return result


def _file_by_id(files: list[dict[str, Any]], file_id: str) -> dict[str, Any]:
    return next((item for item in files if item.get("file_id") == file_id), {})


def _is_empty(file_obj: dict[str, Any]) -> bool:
    text_stats = file_obj.get("text_stats") or {}
    non_whitespace = text_stats.get("non_whitespace_char_count")
    char_count = text_stats.get("char_count")
    return non_whitespace == 0 or (isinstance(char_count, int) and char_count <= 1)


def _canonical_file(files: list[dict[str, Any]]) -> dict[str, Any]:
    non_copy = [item for item in files if not COPY_PATTERN.search(item.get("name") or "")]
    return _newest_file(non_copy or files)


def _newest_file(files: list[dict[str, Any]]) -> dict[str, Any]:
    return max(files, key=lambda item: item.get("modified_time") or "")


def _stale_match(file_obj: dict[str, Any], files: list[dict[str, Any]]) -> dict[str, Any] | None:
    name = file_obj.get("name") or ""
    if not DRAFT_PATTERN.search(name):
        return None
    parents = set(file_obj.get("parents") or [])
    candidates = [
        item
        for item in files
        if item.get("file_id") != file_obj.get("file_id")
        and set(item.get("parents") or []) & parents
        and FINAL_PATTERN.search(item.get("name") or "")
        and (item.get("modified_time") or "") > (file_obj.get("modified_time") or "")
    ]
    if not candidates:
        return None
    return _newest_file(candidates)


def _name_similarity(first: str | None, second: str | None) -> float | None:
    if not first or not second:
        return None
    return round(SequenceMatcher(None, _normalize_name(first), _normalize_name(second)).ratio(), 2)


def _normalize_name(value: str) -> str:
    lowered = value.lower()
    lowered = COPY_PATTERN.sub("", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def _age_days(modified_time: str | None) -> int | None:
    if not modified_time:
        return None
    modified = datetime.fromisoformat(modified_time.replace("Z", "+00:00"))
    now = datetime.fromisoformat(RUN_AT.replace("Z", "+00:00"))
    return max(0, (now - modified).days)


def _default_signals(reason: str) -> list[str]:
    if reason == "empty":
        return ["non_whitespace_char_count_zero", "char_count_below_minimum"]
    if reason == "unknown_project":
        return ["missing_project_id", "missing_source_registry_id"]
    if TEMPORARY_PATTERN.search(reason):
        return ["temporary_name_pattern"]
    return [reason]
