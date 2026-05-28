"""Cloud Run HTTP entrypoint for content-extractor."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from content_extractor.extraction import extract_from_policy_payload
from content_extractor.firestore_writer import (
    firestore_client,
    write_enabled_from_env,
    write_extracted_batch,
)
from content_extractor.pubsub import decode_pubsub_json, pubsub_message_ref
from content_extractor.review_queue import review_queue_enabled_from_env, write_review_queue_batch
from content_extractor.workspace_auth import build_docs_service, build_drive_service, build_sheets_service


def _json_response(handler: BaseHTTPRequestHandler, status: HTTPStatus, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def docs_read_enabled_from_env() -> bool:
    return os.environ.get("DOCS_READ_ENABLED", "false").lower() == "true"


def sheets_read_enabled_from_env() -> bool:
    return os.environ.get("SHEETS_READ_ENABLED", "false").lower() == "true"


def drive_read_enabled_from_env() -> bool:
    return os.environ.get("DRIVE_READ_ENABLED", "false").lower() == "true"


class ContentExtractorHandler(BaseHTTPRequestHandler):
    server_version = "capital-content-extractor/0.1"

    def do_GET(self) -> None:
        if self.path == "/healthz":
            _json_response(self, HTTPStatus.OK, {"status": "ok", "service": "content-extractor"})
            return
        _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path not in {"/extract-content", "/pubsub/extraction"}:
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            if self.path == "/pubsub/extraction":
                batch_ref = pubsub_message_ref(payload)
                payload = decode_pubsub_json(payload)
            else:
                batch_ref = "request://body"
        except (ValueError, json.JSONDecodeError) as exc:
            print(f"invalid_json: {exc}")
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "invalid_json", "detail": str(exc)})
            return

        if docs_read_enabled_from_env():
            docs_service = build_docs_service()
        else:
            docs_service = _NoopDocsService()
        if sheets_read_enabled_from_env():
            sheets_service = build_sheets_service()
        else:
            sheets_service = _NoopSheetsService()
        if drive_read_enabled_from_env():
            drive_service = build_drive_service()
        else:
            drive_service = _NoopDriveService()
        result = extract_from_policy_payload(
            payload,
            batch_ref=batch_ref,
            docs_service=docs_service,
            sheets_service=sheets_service,
            drive_service=drive_service,
            docs_read_enabled=docs_read_enabled_from_env(),
            sheets_read_enabled=sheets_read_enabled_from_env(),
            drive_read_enabled=drive_read_enabled_from_env(),
        )
        if write_enabled_from_env():
            client = firestore_client(
                os.environ.get("GCP_PROJECT_ID", "capital-index-2026"),
                os.environ.get("FIRESTORE_DATABASE", "(default)"),
            )
            result["write"] = write_extracted_batch(result, client=client, write_enabled=True)
            result["review_queue"] = write_review_queue_batch(
                result,
                client=client,
                review_queue_enabled=review_queue_enabled_from_env(),
            )
        else:
            result["write"] = write_extracted_batch(result, client=_NoopClient(), write_enabled=False)
            result["review_queue"] = write_review_queue_batch(
                result,
                client=_NoopClient(),
                review_queue_enabled=False,
            )
        _json_response(self, HTTPStatus.OK, result)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> int:
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), ContentExtractorHandler)
    print(f"content-extractor listening on port {port}")
    server.serve_forever()
    return 0


class _NoopClient:
    def collection(self, collection_name: str) -> Any:
        raise RuntimeError(f"Noop Firestore client cannot write collection {collection_name}")


class _NoopDocsService:
    def documents(self) -> Any:
        raise RuntimeError("Noop Docs service cannot fetch documents")


class _NoopSheetsService:
    def spreadsheets(self) -> Any:
        raise RuntimeError("Noop Sheets service cannot fetch spreadsheets")


class _NoopDriveService:
    def files(self) -> Any:
        raise RuntimeError("Noop Drive service cannot fetch files")


if __name__ == "__main__":
    raise SystemExit(main())
