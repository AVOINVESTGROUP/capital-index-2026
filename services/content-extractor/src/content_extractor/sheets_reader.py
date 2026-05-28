"""Extract readable text from Google Sheets API spreadsheet responses."""

from __future__ import annotations

from typing import Any


def extract_sheet_text(spreadsheet: dict[str, Any]) -> str:
    parts: list[str] = []
    for sheet in spreadsheet.get("sheets", []):
        title = (sheet.get("properties") or {}).get("title") or "Sheet"
        rows = _sheet_rows(sheet)
        if not rows:
            continue
        parts.append(f"Sheet: {title}")
        header = rows[0]
        if header:
            parts.append("Columns: " + " | ".join(header))
        for index, row in enumerate(rows[1:] if header else rows, start=1):
            if not any(cell.strip() for cell in row):
                continue
            if header and len(header) == len(row):
                rendered = " | ".join(f"{key}: {value}" for key, value in zip(header, row))
            else:
                rendered = " | ".join(row)
            parts.append(f"Row {index}: {rendered}")
    return "\n".join(parts)


def make_sheet_result(plan: dict[str, Any], spreadsheet: dict[str, Any]) -> dict[str, Any]:
    text = extract_sheet_text(spreadsheet)
    return {
        "schema_version": "capital.extracted_text.v1",
        "file_id": plan["file_id"],
        "plan_id": plan["plan_id"],
        "sensitivity_class": plan["sensitivity_class"],
        "text_only": plan["text_only"],
        "embedding_allowed": plan["embedding_allowed"],
        "vault_publish_allowed": plan["vault_publish_allowed"],
        "ai_context_allowed": plan["ai_context_allowed"],
        "doc_title": (spreadsheet.get("properties") or {}).get("title", ""),
        "char_count": len(text),
        "text": text,
        "next_action": "classify" if text.strip() else "review_required",
    }


def _sheet_rows(sheet: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for grid in sheet.get("data", []):
        for row in grid.get("rowData", []):
            values = [_cell_text(cell) for cell in row.get("values", [])]
            while values and values[-1] == "":
                values.pop()
            if values:
                rows.append(values)
    return rows


def _cell_text(cell: dict[str, Any]) -> str:
    if "formattedValue" in cell:
        return str(cell["formattedValue"])
    effective = cell.get("effectiveValue") or {}
    for key in ("stringValue", "numberValue", "boolValue", "formulaValue"):
        if key in effective:
            return str(effective[key])
    return ""
