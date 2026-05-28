"""Rules-based source quality classifier for Drive files."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

GOOGLE_DOC = "application/vnd.google-apps.document"
GOOGLE_SHEET = "application/vnd.google-apps.spreadsheet"
GOOGLE_SLIDES = "application/vnd.google-apps.presentation"
TEXT_MIME_TYPES = {
    "text/markdown",
    "text/plain",
    "text/csv",
}

TECHNICAL_EXTENSIONS = re.compile(
    r"\.(ps1|bat|cmd|sh|py|js|ts|json|lock|log|tmp|bak|zip|rar|7z|exe|dll)$",
    re.IGNORECASE,
)
ARCHIVE_PATTERN = re.compile(r"\b(archive|archived|old|backup|bak|obsolete)\b", re.IGNORECASE)
COPY_PATTERN = re.compile(r"\b(copy|копия|duplicate)\b", re.IGNORECASE)
TEMP_PATTERN = re.compile(r"\b(tmp|temp|untitled|без названия|draft|черновик)\b", re.IGNORECASE)
README_PATTERN = re.compile(r"^readme(\.md)?$", re.IGNORECASE)
DATED_CONTEXT_PATTERN = re.compile(r"^(AI_TODAY_CONTEXT|AI_WINDOW_CONTEXT).*?(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
DAILY_NOTE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$", re.IGNORECASE)
PROMPT_TEMPLATE_PATTERN = re.compile(
    r"^(make|rewrite|remove|fix|generate|explain|clip)\b|"
    r"\b(grammar|spelling|tweet|glossary|table of contents|youtube transcript|web page)\b",
    re.IGNORECASE,
)


def classify_source_file(file_record: dict[str, Any]) -> dict[str, Any]:
    """Return a source-quality decision for one /files record.

    The classifier is intentionally conservative. It never mutates Drive and never overrides
    explicit human decisions.
    """

    current_status = file_record.get("source_status") or "needs_human_review"
    if _has_human_decision(file_record):
        return _decision(file_record, current_status, file_record.get("index_eligible") is True, False, "preserve_human_decision", 1.0)

    name = file_record.get("name") or ""
    mime_type = file_record.get("mime_type") or ""

    if _prompt_template(name):
        return _decision(file_record, "do_not_index", False, True, "prompt_template_not_project_context", 0.9)

    if file_record.get("trashed") is True:
        return _decision(file_record, "do_not_index", False, True, "trashed_file", 1.0)

    if _technical_file(name, mime_type):
        return _decision(file_record, "do_not_index", False, True, "technical_or_binary_file", 0.95)

    if ARCHIVE_PATTERN.search(name):
        return _decision(file_record, "candidate_archive", False, False, "archive_name_pattern", 0.86)

    if COPY_PATTERN.search(name):
        return _decision(file_record, "candidate_duplicate", False, False, "copy_name_pattern", 0.86)

    if TEMP_PATTERN.search(name):
        return _decision(file_record, "needs_human_review", False, False, "temporary_or_draft_name", 0.72)

    if _business_readable(name, mime_type):
        return _decision(file_record, "active", True, False, "readable_business_source", 0.8)

    if mime_type == GOOGLE_SLIDES:
        return _decision(file_record, "needs_human_review", False, False, "slides_need_policy", 0.65)

    return _decision(file_record, "needs_human_review", False, False, "no_matching_rule", 0.5)


def classify_batch(files: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = _mark_stale_context(files, [classify_source_file(file_record) for file_record in files])
    return {
        "schema_version": "capital.source_classification_batch.v1",
        "source": "drive_governance.source_classifier",
        "classified_at": _utc_now(),
        "counts": {
            "input_files": len(files),
            "active": sum(1 for item in decisions if item["new_source_status"] == "active"),
            "do_not_index": sum(1 for item in decisions if item["new_source_status"] == "do_not_index"),
            "candidate_cleanup": sum(
                1 for item in decisions if item["new_source_status"].startswith("candidate_")
            ),
            "needs_human_review": sum(
                1 for item in decisions if item["new_source_status"] == "needs_human_review"
            ),
            "preserved": sum(1 for item in decisions if item["rule_id"] == "preserve_human_decision"),
        },
        "decisions": decisions,
    }


def _decision(
    file_record: dict[str, Any],
    new_status: str,
    index_eligible: bool,
    human_block: bool,
    rule_id: str,
    confidence: float,
) -> dict[str, Any]:
    file_id = file_record.get("file_id") or file_record.get("id")
    return {
        "schema_version": "capital.source_classification.v1",
        "file_id": file_id,
        "name": file_record.get("name") or "",
        "mime_type": file_record.get("mime_type") or "",
        "previous_source_status": file_record.get("source_status") or "needs_human_review",
        "previous_index_eligible": file_record.get("index_eligible") is True,
        "previous_human_block": file_record.get("human_block") is True,
        "new_source_status": new_status,
        "new_index_eligible": index_eligible,
        "new_human_block": human_block,
        "rule_id": rule_id,
        "confidence": confidence,
        "drive_mutation": "none",
        "created_at": _utc_now(),
    }


def _has_human_decision(file_record: dict[str, Any]) -> bool:
    updater = file_record.get("source_quality_updated_by")
    if file_record.get("source_approved_by"):
        return True
    return bool(updater and updater != "source_classifier")


def _business_readable(name: str, mime_type: str) -> bool:
    if mime_type in {GOOGLE_DOC, GOOGLE_SHEET}:
        return True
    if mime_type in TEXT_MIME_TYPES:
        return not TECHNICAL_EXTENSIONS.search(name)
    return README_PATTERN.search(name) is not None


def _technical_file(name: str, mime_type: str) -> bool:
    if mime_type in {"application/octet-stream", "application/x-msdownload"}:
        return True
    return TECHNICAL_EXTENSIONS.search(name) is not None


def _prompt_template(name: str) -> bool:
    return PROMPT_TEMPLATE_PATTERN.search(name) is not None


def _mark_stale_context(files: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest_context_date = _latest_date(name for name in (item.get("name") or "" for item in files) if DATED_CONTEXT_PATTERN.search(name))
    latest_daily_note = _latest_date(name for name in (item.get("name") or "" for item in files) if DAILY_NOTE_PATTERN.search(name))
    by_file_id = {decision["file_id"]: decision for decision in decisions}
    for file_record in files:
        file_id = file_record.get("file_id") or file_record.get("id")
        decision = by_file_id.get(file_id)
        if not decision or decision["rule_id"] == "preserve_human_decision":
            continue
        name = file_record.get("name") or ""
        context_match = DATED_CONTEXT_PATTERN.search(name)
        if context_match and latest_context_date and context_match.group(2) < latest_context_date:
            by_file_id[file_id] = _decision(
                file_record,
                "candidate_stale",
                False,
                False,
                "older_dated_context_snapshot",
                0.92,
            )
            continue
        daily_match = DAILY_NOTE_PATTERN.search(name)
        if daily_match and latest_daily_note and name[:10] < latest_daily_note:
            by_file_id[file_id] = _decision(
                file_record,
                "candidate_stale",
                False,
                False,
                "older_daily_note_snapshot",
                0.88,
            )
    return [by_file_id.get(decision["file_id"], decision) for decision in decisions]


def _latest_date(names: Any) -> str | None:
    dates: list[str] = []
    for name in names:
        context_match = DATED_CONTEXT_PATTERN.search(name)
        if context_match:
            dates.append(context_match.group(2))
            continue
        daily_match = DAILY_NOTE_PATTERN.search(name)
        if daily_match:
            dates.append(name[:10])
    return max(dates) if dates else None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
