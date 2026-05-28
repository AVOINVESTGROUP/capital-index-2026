from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "metadata-loader" / "src"))

from metadata_loader.drive_metadata import load_metadata_payload
from metadata_loader.drive_refetch import refetch_authoritative_batch
from metadata_loader.firestore_writer import firestore_client, write_metadata_batch
from metadata_loader.workspace_auth import build_drive_service


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fetch_drive_file(service: Any, file_id: str) -> dict[str, Any]:
    return (
        service.files()
        .get(
            fileId=file_id,
            supportsAllDrives=True,
            fields="id,name,mimeType,parents,trashed,modifiedTime,webViewLink,driveId",
        )
        .execute()
    )


def normalized_event(file_obj: dict[str, Any], *, index: int) -> dict[str, Any]:
    file_id = file_obj["id"]
    observed_at = utc_now()
    return {
        "schema_version": "capital.normalized_drive_event.v1",
        "event_id": f"evt_live_metadata_{file_id[:16]}",
        "event_type": "drive.file.changed",
        "source": "drive_changes_api",
        "gcp_project_id": "capital-index-2026",
        "project_id": "capital_index",
        "source_registry_id": "manual_live_probe",
        "file_id": file_id,
        "trace_id": f"trace_live_metadata_{index}",
        "idempotency_key": f"live_metadata_probe:{file_id}",
        "observed_at": observed_at,
        "raw_payload_ref": "request://live_metadata_probe",
        "review_required": False,
        "review_reason": None,
        "file": {
            "id": file_id,
            "name": file_obj.get("name"),
            "mime_type": file_obj.get("mimeType"),
            "parents": file_obj.get("parents") or [],
            "trashed": file_obj.get("trashed", False),
            "modified_time": file_obj.get("modifiedTime"),
            "web_view_link": file_obj.get("webViewLink"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Controlled live /files metadata upsert.")
    parser.add_argument("--file-id", action="append", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    service = build_drive_service()
    events = [
        normalized_event(fetch_drive_file(service, file_id), index=index)
        for index, file_id in enumerate(args.file_id)
    ]
    payload = {
        "schema_version": "capital.normalized_drive_event_batch.v1",
        "source": "live_metadata_probe",
        "gcp_project_id": "capital-index-2026",
        "project_id": "capital_index",
        "source_registry_id": "manual_live_probe",
        "events": events,
    }
    result = load_metadata_payload(payload, batch_ref="request://live_metadata_probe")
    result = refetch_authoritative_batch(result, service=service, refetch_enabled=True)
    client = firestore_client("capital-index-2026", "(default)") if args.write else _NoopClient()
    write = write_metadata_batch(result, client=client, write_enabled=args.write)

    print(
        json.dumps(
            {
                "counts": result["counts"],
                "authoritative_refetch": result.get("authoritative_refetch"),
                "files": [
                    {
                        "file_id": (item.get("file") or {}).get("file_id"),
                        "name": (item.get("file") or {}).get("name"),
                        "mime_type": (item.get("file") or {}).get("mime_type"),
                        "metadata_status": item.get("metadata_status"),
                        "review_required": item.get("review_required"),
                        "review_reason": item.get("review_reason"),
                    }
                    for item in result.get("file_upserts", [])
                ],
                "write": write,
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
