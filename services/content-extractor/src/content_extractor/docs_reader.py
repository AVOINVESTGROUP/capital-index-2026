"""Extract plain text from a Google Docs API document response."""

from __future__ import annotations

from typing import Any


def extract_text(doc: dict[str, Any]) -> str:
    """Traverse Docs API body structure and return plain text."""
    parts: list[str] = []

    for element in doc.get("body", {}).get("content", []):
        if "paragraph" in element:
            _collect_paragraph(element["paragraph"], parts)
        elif "table" in element:
            for row in element["table"].get("tableRows", []):
                for cell in row.get("tableCells", []):
                    for cell_el in cell.get("content", []):
                        if "paragraph" in cell_el:
                            _collect_paragraph(cell_el["paragraph"], parts)

    return "".join(parts)


def _collect_paragraph(paragraph: dict[str, Any], parts: list[str]) -> None:
    for pe in paragraph.get("elements", []):
        text_run = pe.get("textRun")
        if text_run:
            parts.append(text_run.get("content", ""))


def make_extraction_result(
    plan: dict[str, Any],
    doc: dict[str, Any],
) -> dict[str, Any]:
    """Return a structured extraction result from an extraction plan and Docs API response."""

    text = extract_text(doc)

    return {
        "schema_version": "capital.extracted_text.v1",
        "file_id": plan["file_id"],
        "plan_id": plan["plan_id"],
        "sensitivity_class": plan["sensitivity_class"],
        "text_only": plan["text_only"],
        "embedding_allowed": plan["embedding_allowed"],
        "vault_publish_allowed": plan["vault_publish_allowed"],
        "ai_context_allowed": plan["ai_context_allowed"],
        "doc_title": doc.get("title", ""),
        "char_count": len(text),
        "text": text,
        "next_action": "classify" if text.strip() else "review_required",
    }
