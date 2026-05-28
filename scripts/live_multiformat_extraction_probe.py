from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "content-extractor" / "src"))

from content_extractor.extraction import extract_from_policy_payload
from content_extractor.firestore_writer import firestore_client, write_extracted_batch
from content_extractor.workspace_auth import build_docs_service, build_drive_service, build_sheets_service


def _decision(file_id: str, name: str, mime_type: str) -> dict[str, Any]:
    return {
        "schema_version": "capital.policy_decision.v1",
        "decision_id": f"policy_live_{file_id[:16]}",
        "source": "live_multiformat_probe",
        "source_load_id": None,
        "source_event_id": None,
        "trace_id": "trace_live_multiformat_probe",
        "idempotency_key": f"live_multiformat_probe:{file_id}",
        "raw_metadata_ref": "request://live_multiformat_probe",
        "decided_at": "",
        "policy_snapshot_id": "manual_live_multiformat_probe",
        "policy_id": "folder_policies/manual_probe",
        "policy_name": "Manual live multiformat probe",
        "gcp_project_id": "capital-index-2026",
        "project_id": "capital_index",
        "source_registry_id": "manual_probe",
        "file_id": file_id,
        "name": name,
        "mime_type": mime_type,
        "web_view_link": None,
        "sensitivity_class": "PUBLIC_INTERNAL",
        "allowed_actions": ["read_content"],
        "denied_actions": ["embed", "publish_to_vault", "include_in_ai_context"],
        "approval_required_for": [],
        "review_required": False,
        "review_reason": None,
        "next_action": "content_extraction_candidate",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Controlled live extraction for Markdown and Sheets.")
    parser.add_argument("--md-id", required=True)
    parser.add_argument("--md-name", default="2026-05-27.md")
    parser.add_argument("--sheet-id", required=True)
    parser.add_argument("--sheet-name", default="AI_Bridge_Log_Spreadsheet")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    payload = {
        "policy_decisions": [
            _decision(args.md_id, args.md_name, "text/markdown"),
            _decision(args.sheet_id, args.sheet_name, "application/vnd.google-apps.spreadsheet"),
        ]
    }
    result = extract_from_policy_payload(
        payload,
        batch_ref="request://live_multiformat_probe",
        docs_service=build_docs_service(),
        sheets_service=build_sheets_service(),
        drive_service=build_drive_service(),
        docs_read_enabled=True,
        sheets_read_enabled=True,
        drive_read_enabled=True,
    )

    summary = []
    for item in result["extracted_text"]:
        text = item.get("text") or ""
        summary.append(
            {
                "file_id": item.get("file_id"),
                "doc_title": item.get("doc_title"),
                "char_count": item.get("char_count"),
                "next_action": item.get("next_action"),
                "review_required": item.get("review_required"),
                "review_reason": item.get("review_reason"),
                "preview": text[:240].replace("\n", "\\n"),
            }
        )

    if args.write:
        client = firestore_client("capital-index-2026", "(default)")
        write_result = write_extracted_batch(result, client=client, write_enabled=True)
    else:
        write_result = write_extracted_batch(result, client=_NoopClient(), write_enabled=False)

    print(
        json.dumps(
            {
                "counts": result["counts"],
                "items": summary,
                "write": write_result,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


class _NoopClient:
    def collection(self, collection_name: str) -> Any:
        raise RuntimeError(f"Noop Firestore client cannot write collection {collection_name}")


if __name__ == "__main__":
    raise SystemExit(main())
