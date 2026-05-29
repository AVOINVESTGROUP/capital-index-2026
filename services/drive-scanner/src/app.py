"""Cloud Run HTTP entrypoint for controlled Drive scan reconciliation."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from drive_scanner.scanner import inventory_to_normalized_events, scan_all_drive_files, scan_drive
from metadata_loader.drive_metadata import load_metadata_payload
from metadata_loader.drive_refetch import refetch_authoritative_batch
from metadata_loader.firestore_writer import firestore_client, write_metadata_batch
from metadata_loader.workspace_auth import build_drive_service


def _json_response(handler: BaseHTTPRequestHandler, status: HTTPStatus, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _request_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    content_length = int(handler.headers.get("Content-Length", "0"))
    if content_length == 0:
        return {}
    return json.loads(handler.rfile.read(content_length).decode("utf-8"))


class DriveScannerHandler(BaseHTTPRequestHandler):
    server_version = "capital-drive-scanner/0.1"

    def do_GET(self) -> None:
        if self.path == "/healthz":
            _json_response(self, HTTPStatus.OK, {"status": "ok", "service": "drive-scanner"})
            return
        _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/scan-drive":
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        try:
            payload = _request_json(self)
            result = run_scan(payload)
        except (ValueError, json.JSONDecodeError) as exc:
            print(f"bad_request: {exc}")
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "bad_request", "detail": str(exc)})
            return
        except Exception as exc:  # pragma: no cover - Cloud Run logs need the exact failure.
            print(f"scan_failed: {type(exc).__name__}: {exc}")
            _json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "scan_failed", "detail": str(exc)})
            return

        _json_response(self, HTTPStatus.OK, result)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def run_scan(payload: dict[str, Any]) -> dict[str, Any]:
    scan_mode = _scan_mode(payload)
    root_folder_ids = _root_folder_ids(payload)
    if scan_mode == "roots" and not root_folder_ids:
        raise ValueError("root_folder_ids is required when scan_mode=roots")

    project_id = os.environ.get("GCP_PROJECT_ID", "capital-index-2026")
    database = os.environ.get("FIRESTORE_DATABASE", "(default)")
    business_project_id = payload.get("project_id") or os.environ.get("BUSINESS_PROJECT_ID", "capital_index")
    source_registry_id = payload.get("source_registry_id") or os.environ.get(
        "SOURCE_REGISTRY_ID", "drive_scan"
    )
    max_files = _bounded_int(payload.get("max_files") or os.environ.get("MAX_FILES") or "250", 1, 10000)

    drive_service = build_drive_service()
    include_folders = payload.get("include_folders") is True
    if scan_mode == "all_drive":
        inventory = scan_all_drive_files(
            drive_service,
            max_files=max_files,
            include_folders=include_folders,
        )
    else:
        inventory = scan_drive(
            drive_service,
            root_folder_ids=root_folder_ids,
            max_files=max_files,
            include_folders=include_folders,
        )
    event_batch = inventory_to_normalized_events(
        inventory,
        gcp_project_id=project_id,
        project_id=business_project_id,
        source_registry_id=source_registry_id,
    )
    metadata_batch = load_metadata_payload(event_batch, batch_ref="request://drive_scanner")
    refetch_enabled = _refetch_enabled(payload)
    metadata_batch = refetch_authoritative_batch(
        metadata_batch,
        service=drive_service,
        refetch_enabled=refetch_enabled,
    )
    write_enabled = _request_write_enabled(payload)
    write = write_metadata_batch(
        metadata_batch,
        client=firestore_client(project_id, database) if write_enabled else _NoopClient(),
        write_enabled=write_enabled,
    )

    return {
        "service": "drive-scanner",
        "write_requested": payload.get("write") is True,
        "write_enabled": write_enabled,
        "request_write_enabled": os.environ.get("REQUEST_WRITE_ENABLED", "false").lower() == "true",
        "scan_mode": scan_mode,
        "refetch_authoritative": refetch_enabled,
        "root_folder_ids": root_folder_ids,
        "inventory_counts": inventory["counts"],
        "metadata_counts": metadata_batch["counts"],
        "write": write,
        "files": [
            {
                "file_id": (item.get("file") or {}).get("file_id"),
                "name": (item.get("file") or {}).get("name"),
                "mime_type": (item.get("file") or {}).get("mime_type"),
                "metadata_status": item.get("metadata_status"),
            }
            for item in metadata_batch.get("file_upserts", [])[:20]
        ],
    }


def _root_folder_ids(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("root_folder_ids") or os.environ.get("DRIVE_SCAN_ROOT_FOLDER_IDS", "")
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def _scan_mode(payload: dict[str, Any]) -> str:
    raw = str(payload.get("scan_mode") or os.environ.get("DRIVE_SCAN_MODE") or "roots").strip().lower()
    if raw in {"all", "all_drive", "all-drives", "all_drives"}:
        return "all_drive"
    if raw in {"roots", "root", "folders"}:
        return "roots"
    raise ValueError("scan_mode must be roots or all_drive")


def _request_write_enabled(payload: dict[str, Any]) -> bool:
    if os.environ.get("WRITE_ENABLED", "false").lower() == "true":
        return True
    request_write_allowed = os.environ.get("REQUEST_WRITE_ENABLED", "false").lower() == "true"
    return request_write_allowed and payload.get("write") is True


def _refetch_enabled(payload: dict[str, Any]) -> bool:
    if payload.get("refetch_authoritative") is True:
        return True
    return os.environ.get("DRIVE_REFETCH_ENABLED", "false").lower() == "true"


def _bounded_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return minimum
    return max(minimum, min(parsed, maximum))


def main() -> int:
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), DriveScannerHandler)
    print(f"drive-scanner listening on port {port}")
    server.serve_forever()
    return 0


class _NoopClient:
    def collection(self, collection_name: str) -> Any:
        raise RuntimeError(f"Noop Firestore client cannot write collection {collection_name}")


if __name__ == "__main__":
    raise SystemExit(main())
