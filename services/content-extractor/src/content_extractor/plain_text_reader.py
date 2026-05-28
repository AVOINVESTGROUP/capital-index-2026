"""Read plain text files downloaded from Drive."""

from __future__ import annotations

from typing import Any

TEXT_MIME_TYPES = {
    "text/markdown",
    "text/plain",
    "text/x-markdown",
}

TEXT_EXTENSIONS = (".md", ".markdown", ".txt")


def is_plain_text_file(plan: dict[str, Any]) -> bool:
    mime_type = plan.get("mime_type")
    name = (plan.get("name") or "").lower()
    return mime_type in TEXT_MIME_TYPES or name.endswith(TEXT_EXTENSIONS)


def decode_text_payload(payload: bytes | str) -> str:
    if isinstance(payload, str):
        return payload
    for encoding in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


def make_plain_text_result(plan: dict[str, Any], payload: bytes | str) -> dict[str, Any]:
    text = decode_text_payload(payload)
    return {
        "schema_version": "capital.extracted_text.v1",
        "file_id": plan["file_id"],
        "plan_id": plan["plan_id"],
        "sensitivity_class": plan["sensitivity_class"],
        "text_only": plan["text_only"],
        "embedding_allowed": plan["embedding_allowed"],
        "vault_publish_allowed": plan["vault_publish_allowed"],
        "ai_context_allowed": plan["ai_context_allowed"],
        "doc_title": plan.get("name") or "",
        "char_count": len(text),
        "text": text,
        "next_action": "classify" if text.strip() else "review_required",
    }
