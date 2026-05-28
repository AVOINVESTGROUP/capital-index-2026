from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from google.cloud import firestore

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "content-extractor" / "src"))

from content_extractor.extraction import (  # noqa: E402
    GOOGLE_DOC_MIME,
    GOOGLE_SHEET_MIME,
    extract_from_policy_payload,
)
from content_extractor.firestore_writer import write_extracted_batch  # noqa: E402
from content_extractor.plain_text_reader import is_plain_text_file  # noqa: E402
from content_extractor.workspace_auth import (  # noqa: E402
    build_docs_service,
    build_drive_service,
    build_sheets_service,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract readable content from approved source files.")
    parser.add_argument("--project", default="capital-index-2026")
    parser.add_argument("--database", default="(default)")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    db = firestore.Client(project=args.project, database=args.database)
    files = _eligible_files(db, args.limit)
    existing_ids = _existing_extracted_ids(db) if not args.force else set()
    candidates = [item for item in files if item["file_id"] not in existing_ids and _supported(item)]
    payload = {
        "schema_version": "capital.policy_decision_batch.v1",
        "source": "extract_approved_content",
        "gcp_project_id": args.project,
        "project_id": "capital_index",
        "source_registry_id": "drive_scan",
        "policy_decisions": [_decision(item) for item in candidates],
    }
    if not candidates:
        print(
            json.dumps(
                {
                    "write_enabled": args.write,
                    "eligible_files": len(files),
                    "skipped_existing": len(files),
                    "candidates": 0,
                    "counts": {"input_policy_decisions": 0, "extracted_text": 0, "review_required": 0},
                    "write": {
                        "status": "disabled" if not args.write else "written",
                        "collection": "extracted_text",
                        "attempted": 0,
                        "file_ids": [],
                    },
                    "items": [],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    result = extract_from_policy_payload(
        payload,
        batch_ref="firestore://files/approved",
        docs_service=build_docs_service(),
        sheets_service=build_sheets_service(),
        drive_service=build_drive_service(),
        docs_read_enabled=True,
        sheets_read_enabled=True,
        drive_read_enabled=True,
    )
    write = write_extracted_batch(result, client=db, write_enabled=args.write)
    print(
        json.dumps(
            {
                "write_enabled": args.write,
                "eligible_files": len(files),
                "skipped_existing": len(files) - len(candidates),
                "candidates": len(candidates),
                "counts": result["counts"],
                "write": write,
                "items": [
                    {
                        "file_id": item.get("file_id"),
                        "title": item.get("doc_title"),
                        "char_count": item.get("char_count"),
                        "next_action": item.get("next_action"),
                        "review_reason": item.get("review_reason"),
                    }
                    for item in result.get("extracted_text", [])
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _eligible_files(db: firestore.Client, limit: int) -> list[dict[str, Any]]:
    docs = (
        db.collection("files")
        .where("source_status", "==", "active")
        .where("index_eligible", "==", True)
        .limit(limit)
        .stream()
    )
    return [doc.to_dict() | {"file_id": doc.to_dict().get("file_id") or doc.id} for doc in docs]


def _existing_extracted_ids(db: firestore.Client) -> set[str]:
    return {doc.id for doc in db.collection("extracted_text").limit(1000).stream()}


def _supported(file_record: dict[str, Any]) -> bool:
    mime_type = file_record.get("mime_type")
    return mime_type in {GOOGLE_DOC_MIME, GOOGLE_SHEET_MIME} or is_plain_text_file(file_record)


def _decision(file_record: dict[str, Any]) -> dict[str, Any]:
    file_id = file_record["file_id"]
    return {
        "schema_version": "capital.policy_decision.v1",
        "decision_id": f"policy_approved_{file_id[:18]}",
        "source": "extract_approved_content",
        "source_load_id": file_record.get("last_metadata_load_id"),
        "source_event_id": file_record.get("last_source_event_id"),
        "trace_id": f"trace_extract_approved_{file_id[:18]}",
        "idempotency_key": f"extract_approved_content:{file_id}:{file_record.get('modified_time') or ''}",
        "raw_metadata_ref": f"firestore://files/{file_id}",
        "decided_at": "",
        "policy_snapshot_id": "manual_approved_sources",
        "policy_id": "folder_policies/approved_sources",
        "policy_name": "Approved source content extraction",
        "gcp_project_id": file_record.get("gcp_project_id") or "capital-index-2026",
        "project_id": file_record.get("project_id") or "capital_index",
        "source_registry_id": file_record.get("source_registry_id") or "drive_scan",
        "file_id": file_id,
        "name": file_record.get("name"),
        "mime_type": file_record.get("mime_type"),
        "web_view_link": file_record.get("web_view_link"),
        "sensitivity_class": "PUBLIC_INTERNAL",
        "allowed_actions": ["read_content"],
        "denied_actions": ["embed", "publish_to_vault", "include_in_ai_context"],
        "approval_required_for": [],
        "review_required": False,
        "review_reason": None,
        "next_action": "content_extraction_candidate",
    }


if __name__ == "__main__":
    raise SystemExit(main())
