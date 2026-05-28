"""Cloud Run HTTP entrypoint for drive-governance."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from drive_governance.firestore_writer import (
    firestore_client,
    write_enabled_from_env,
    write_governance_batch,
)
from drive_governance.governance import evaluate_inventory
from drive_governance.inventory import build_inventory_from_firestore
from drive_governance.source_classification_writer import write_source_classification_batch
from drive_governance.source_classifier import classify_batch


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


class DriveGovernanceHandler(BaseHTTPRequestHandler):
    server_version = "capital-drive-governance/0.1"

    def do_GET(self) -> None:
        if self.path == "/healthz":
            _json_response(self, HTTPStatus.OK, {"status": "ok", "service": "drive-governance"})
            return
        _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path not in {"/evaluate-governance", "/classify-sources"}:
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        try:
            payload = _request_json(self)
        except (ValueError, json.JSONDecodeError) as exc:
            print(f"invalid_json: {exc}")
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "invalid_json", "detail": str(exc)})
            return

        client = firestore_client(
            os.environ.get("GCP_PROJECT_ID", "capital-index-2026"),
            os.environ.get("FIRESTORE_DATABASE", "(default)"),
        )
        limit = _inventory_limit(payload)
        inventory = payload.get("inventory") or build_inventory_from_firestore(
            client=client,
            limit=limit,
            fixture_id="firestore_inventory",
        )
        if self.path == "/classify-sources":
            result = classify_batch(inventory.get("files") or [])
            write_enabled = _request_write_enabled(payload)
            result["write_requested"] = bool(payload.get("write"))
            result["request_write_enabled"] = os.environ.get("REQUEST_WRITE_ENABLED", "false").lower() == "true"
            result["write"] = write_source_classification_batch(
                result,
                client=client if write_enabled else _NoopClient(),
                write_enabled=write_enabled,
            )
            _json_response(self, HTTPStatus.OK, result)
            return

        result = evaluate_inventory(inventory)
        result["inventory_source"] = "request_body" if payload.get("inventory") else "firestore"
        write_enabled = _request_write_enabled(payload)
        result["write_requested"] = bool(payload.get("write"))
        result["request_write_enabled"] = os.environ.get("REQUEST_WRITE_ENABLED", "false").lower() == "true"
        result["write"] = write_governance_batch(
            result,
            client=client if write_enabled else _NoopClient(),
            write_enabled=write_enabled,
        )
        _json_response(self, HTTPStatus.OK, result)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def _inventory_limit(payload: dict[str, Any]) -> int:
    value = payload.get("limit") or os.environ.get("INVENTORY_LIMIT") or "250"
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 250
    return max(1, min(parsed, 1000))


def _request_write_enabled(payload: dict[str, Any]) -> bool:
    if write_enabled_from_env():
        return True
    request_write_allowed = os.environ.get("REQUEST_WRITE_ENABLED", "false").lower() == "true"
    return request_write_allowed and payload.get("write") is True


def main() -> int:
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), DriveGovernanceHandler)
    print(f"drive-governance listening on port {port}")
    server.serve_forever()
    return 0


class _NoopClient:
    def collection(self, collection_name: str) -> Any:
        raise RuntimeError(f"Noop Firestore client cannot write collection {collection_name}")


if __name__ == "__main__":
    raise SystemExit(main())
