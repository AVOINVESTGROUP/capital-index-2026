"""Classify CAPITAL_INDEX_2026 Sheet rows with a server-side AI provider."""

from __future__ import annotations

import json
import re
from typing import Any, Callable


PROJECTS = [
    "Integra Motors Dubai",
    "Axon Agency",
    "Leaders Advocates",
    "Maritime Wolf Advisory",
    "Ювелирный дом Золотов",
    "AvoInvestGroup",
    "AVOuniverse",
    "100Trust",
    "Контент-завод",
    "Капитал-индекс",
    "Личное",
    "UNCATEGORIZED",
]

ALLOWED_ACTIONS = {"KEEP", "DELETE", "REVIEW"}


class SheetClassificationProvider:
    provider_id: str
    model_id: str

    def generate_json(self, *, system: str, user: str) -> dict[str, Any]:
        raise NotImplementedError


def classify_sheet_row(
    row: dict[str, Any],
    *,
    provider: SheetClassificationProvider | Callable[[dict[str, str]], dict[str, Any]],
) -> dict[str, Any]:
    """Return a normalized Sheet row classification."""

    prompt = build_sheet_classification_prompt(row)
    if callable(provider):
        raw = provider(prompt)
    else:
        raw = provider.generate_json(system=prompt["system"], user=prompt["user"])
    return normalize_sheet_classification(raw)


def build_sheet_classification_prompt(row: dict[str, Any]) -> dict[str, str]:
    name = _text(row.get("file_name") or row.get("name"))
    folder = _text(row.get("parent_folder_name"))
    mime_type = _text(row.get("mime_type"))
    content = _text(row.get("content"))[:2500]

    return {
        "system": (
            "You classify files for CAPITAL INDEX 2026. Return only JSON. "
            "Do not approve restricted access, do not request deletion, and do not invent file contents. "
            "Use DELETE only as a table action recommendation for obvious junk/duplicates/empty files; "
            "it never means deleting Drive files automatically."
        ),
        "user": (
            "Analyze one file metadata/content snippet for Alexander Tyurin's capital index.\n\n"
            f"Known projects: {', '.join(PROJECTS)}.\n\n"
            f"File name: {name}\n"
            f"Parent folder: {folder}\n"
            f"MIME type: {mime_type}\n"
            f"Text snippet:\n{content}\n\n"
            "Return this JSON object with exactly these keys:\n"
            "{"
            '"project":"", '
            '"sub_topic":"", '
            '"type":"", '
            '"summary_50w":"", '
            '"linked_projects":"", '
            '"value_score":1, '
            '"action":"KEEP"'
            "}"
        ),
    }


def normalize_sheet_classification(raw: dict[str, Any]) -> dict[str, Any]:
    project = _text(raw.get("project")) or "UNCATEGORIZED"
    action = _text(raw.get("action")).upper()
    if action not in ALLOWED_ACTIONS:
        action = "REVIEW"

    return {
        "project": project,
        "sub_topic": _text(raw.get("sub_topic")),
        "type": _text(raw.get("type")),
        "summary_50w": _trim_words(_text(raw.get("summary_50w")), 70),
        "linked_projects": _text(raw.get("linked_projects")),
        "value_score": _value_score(raw.get("value_score")),
        "action": action,
    }


def parse_sheet_classification_response(value: str) -> dict[str, Any]:
    return normalize_sheet_classification(json.loads(value))


def _value_score(value: Any) -> int:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return 1
    return max(1, min(parsed, 5))


def _trim_words(value: str, limit: int) -> str:
    words = re.split(r"\s+", value.strip())
    if len(words) <= limit:
        return value.strip()
    return " ".join(words[:limit])


def _text(value: Any) -> str:
    return str(value or "").strip()
