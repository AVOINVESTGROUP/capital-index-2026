"""Build extraction results from policy decision batches."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Protocol

from content_extractor.docs_reader import make_extraction_result
from content_extractor.plain_text_reader import is_plain_text_file, make_plain_text_result
from content_extractor.sheets_reader import make_sheet_result

GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
GOOGLE_SHEET_MIME = "application/vnd.google-apps.spreadsheet"


class DocsExecute(Protocol):
    def execute(self) -> dict[str, Any]:
        ...


class DocsDocumentsResource(Protocol):
    def get(self, **kwargs: Any) -> DocsExecute:
        ...


class DocsService(Protocol):
    def documents(self) -> DocsDocumentsResource:
        ...

class SheetsSpreadsheetsResource(Protocol):
    def get(self, **kwargs: Any) -> DocsExecute:
        ...


class SheetsService(Protocol):
    def spreadsheets(self) -> SheetsSpreadsheetsResource:
        ...


class DriveFilesResource(Protocol):
    def get_media(self, **kwargs: Any) -> DocsExecute:
        ...


class DriveService(Protocol):
    def files(self) -> DriveFilesResource:
        ...


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def extraction_plan(decision: dict[str, Any], *, batch_ref: str, index: int) -> dict[str, Any]:
    allowed = decision.get("allowed_actions") or []
    denied = decision.get("denied_actions") or []
    plan_material = _compact_json(
        {
            "decision_id": decision.get("decision_id"),
            "file_id": decision.get("file_id"),
            "policy_id": decision.get("policy_id"),
        }
    )
    return {
        "schema_version": "capital.extraction_plan.v1",
        "plan_id": f"extract_{_stable_hash(plan_material)[:24]}",
        "source_decision_id": decision.get("decision_id"),
        "source_event_id": decision.get("source_event_id"),
        "source_load_id": decision.get("source_load_id"),
        "trace_id": decision.get("trace_id"),
        "idempotency_key": decision.get("idempotency_key"),
        "raw_policy_ref": f"{batch_ref}#/policy_decisions/{index}",
        "planned_at": _utc_now(),
        "file_id": decision.get("file_id"),
        "name": decision.get("name"),
        "mime_type": decision.get("mime_type"),
        "gcp_project_id": decision.get("gcp_project_id"),
        "project_id": decision.get("project_id"),
        "source_registry_id": decision.get("source_registry_id"),
        "sensitivity_class": decision.get("sensitivity_class"),
        "text_only": True,
        "embedding_allowed": "embed" in allowed and "embed" not in denied,
        "vault_publish_allowed": "publish_to_vault" in allowed and "publish_to_vault" not in denied,
        "ai_context_allowed": "include_in_ai_context" in allowed and "include_in_ai_context" not in denied,
        "read_content_allowed": "read_content" in allowed and "read_content" not in denied,
        "review_required": decision.get("review_required", False),
        "review_reason": decision.get("review_reason"),
    }


def fetch_doc(service: DocsService, document_id: str) -> dict[str, Any]:
    return service.documents().get(documentId=document_id).execute()


def fetch_sheet(service: SheetsService, spreadsheet_id: str) -> dict[str, Any]:
    return service.spreadsheets().get(spreadsheetId=spreadsheet_id, includeGridData=True).execute()


def fetch_plain_text(service: DriveService, file_id: str) -> bytes | str:
    return service.files().get_media(fileId=file_id).execute()


def extract_from_policy_payload(
    payload: dict[str, Any],
    *,
    batch_ref: str,
    docs_service: DocsService,
    sheets_service: SheetsService | None = None,
    drive_service: DriveService | None = None,
    docs_read_enabled: bool,
    sheets_read_enabled: bool | None = None,
    drive_read_enabled: bool | None = None,
) -> dict[str, Any]:
    decisions = payload.get("policy_decisions") or []
    results: list[dict[str, Any]] = []
    sheets_enabled = docs_read_enabled if sheets_read_enabled is None else sheets_read_enabled
    drive_enabled = docs_read_enabled if drive_read_enabled is None else drive_read_enabled

    for index, decision in enumerate(decisions):
        plan = extraction_plan(decision, batch_ref=batch_ref, index=index)
        if plan["review_required"]:
            results.append(_review_result(plan, plan["review_reason"] or "policy_review_required"))
            continue
        if not plan["read_content_allowed"]:
            results.append(_review_result(plan, "read_content_not_allowed"))
            continue
        if not _format_read_enabled(plan, docs_read_enabled, sheets_enabled, drive_enabled):
            results.append(_pending_result(plan, "content_read_disabled"))
            continue

        result = _extract_plan_content(
            plan,
            docs_service=docs_service,
            sheets_service=sheets_service,
            drive_service=drive_service,
        )
        results.append(
            {
                **result,
                "source_decision_id": plan["source_decision_id"],
                "source_event_id": plan["source_event_id"],
                "source_load_id": plan["source_load_id"],
                "trace_id": plan["trace_id"],
                "idempotency_key": plan["idempotency_key"],
                "raw_policy_ref": plan["raw_policy_ref"],
                "extracted_at": _utc_now(),
                "review_required": result["next_action"] == "review_required",
                "review_reason": "empty_text" if result["next_action"] == "review_required" else None,
            }
        )

    return {
        "schema_version": "capital.extracted_text_batch.v1",
        "source": "content_extractor",
        "input_batch_ref": batch_ref,
        "run_at": _utc_now(),
        "gcp_project_id": payload.get("gcp_project_id"),
        "project_id": payload.get("project_id"),
        "source_registry_id": payload.get("source_registry_id"),
        "counts": {
            "input_policy_decisions": len(decisions),
            "extracted_text": len(results),
            "review_required": sum(1 for item in results if item.get("review_required")),
        },
        "extracted_text": results,
    }


def _review_result(plan: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "schema_version": "capital.extracted_text.v1",
        "file_id": plan["file_id"],
        "plan_id": plan["plan_id"],
        "sensitivity_class": plan["sensitivity_class"],
        "text_only": plan["text_only"],
        "embedding_allowed": plan["embedding_allowed"],
        "vault_publish_allowed": plan["vault_publish_allowed"],
        "ai_context_allowed": plan["ai_context_allowed"],
        "doc_title": "",
        "char_count": 0,
        "text": "",
        "next_action": "review_required",
        "source_decision_id": plan["source_decision_id"],
        "source_event_id": plan["source_event_id"],
        "source_load_id": plan["source_load_id"],
        "trace_id": plan["trace_id"],
        "idempotency_key": plan["idempotency_key"],
        "raw_policy_ref": plan["raw_policy_ref"],
        "extracted_at": _utc_now(),
        "review_required": True,
        "review_reason": reason,
    }


def _pending_result(plan: dict[str, Any], reason: str) -> dict[str, Any]:
    result = _review_result(plan, reason)
    return {**result, "next_action": "pending", "review_required": False}


def _format_read_enabled(
    plan: dict[str, Any],
    docs_enabled: bool,
    sheets_enabled: bool,
    drive_enabled: bool,
) -> bool:
    mime_type = plan.get("mime_type")
    if mime_type == GOOGLE_DOC_MIME:
        return docs_enabled
    if mime_type == GOOGLE_SHEET_MIME:
        return sheets_enabled
    if is_plain_text_file(plan):
        return drive_enabled
    return docs_enabled


def _extract_plan_content(
    plan: dict[str, Any],
    *,
    docs_service: DocsService,
    sheets_service: SheetsService | None,
    drive_service: DriveService | None,
) -> dict[str, Any]:
    mime_type = plan.get("mime_type")
    if mime_type == GOOGLE_DOC_MIME:
        doc = fetch_doc(docs_service, plan["file_id"])
        return make_extraction_result(plan, doc)
    if mime_type == GOOGLE_SHEET_MIME:
        if sheets_service is None:
            return _review_result(plan, "sheets_service_unavailable")
        sheet = fetch_sheet(sheets_service, plan["file_id"])
        return make_sheet_result(plan, sheet)
    if is_plain_text_file(plan):
        if drive_service is None:
            return _review_result(plan, "drive_service_unavailable")
        payload = fetch_plain_text(drive_service, plan["file_id"])
        return make_plain_text_result(plan, payload)
    return _review_result(plan, "unsupported_mime_type")
