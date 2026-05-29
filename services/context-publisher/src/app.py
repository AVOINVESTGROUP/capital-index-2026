"""Cloud Run HTTP entrypoint for CAPITAL INDEX context publishing."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from context_publisher.ai_reading import (
    ai_reading_enabled_from_env,
    build_bundle_reading,
    disabled_bundle_reading,
    failed_bundle_reading,
)
from context_publisher.builder import build_second_brain_publication
from context_publisher.firestore_writer import (
    firestore_client,
    write_context_publication,
    write_enabled_from_env,
)
from context_publisher.inventory import build_context_source_from_firestore


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


class ContextPublisherHandler(BaseHTTPRequestHandler):
    server_version = "capital-context-publisher/0.1"

    def do_GET(self) -> None:
        if self.path == "/healthz":
            _json_response(self, HTTPStatus.OK, {"status": "ok", "service": "context-publisher"})
            return
        _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/publish-context":
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        try:
            payload = _request_json(self)
            result = run_publish(payload)
        except (ValueError, json.JSONDecodeError) as exc:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "bad_request", "detail": str(exc)})
            return
        except Exception as exc:  # pragma: no cover - Cloud Run logs need concrete failures.
            print(f"context_publish_failed: {type(exc).__name__}: {exc}")
            _json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "publish_failed", "detail": str(exc)})
            return

        _json_response(self, HTTPStatus.OK, result)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def run_publish(payload: dict[str, Any]) -> dict[str, Any]:
    project_id = os.environ.get("GCP_PROJECT_ID", "capital-index-2026")
    database = os.environ.get("FIRESTORE_DATABASE", "(default)")
    limit = _bounded_int(payload.get("limit") or os.environ.get("CONTEXT_SOURCE_LIMIT") or "1000", 1, 10_000)
    max_bundle_bytes = _bounded_int(
        payload.get("max_bundle_bytes") or os.environ.get("MAX_BUNDLE_BYTES") or "120000",
        10_000,
        500_000,
    )
    client = firestore_client(project_id, database)
    source = payload.get("source") or build_context_source_from_firestore(
        client=client,
        limit=limit,
        owner_profile=payload.get("owner_profile") if isinstance(payload.get("owner_profile"), dict) else None,
        policy_snapshot_id=payload.get("policy_snapshot_id"),
    )
    publication = build_second_brain_publication(
        source,
        bundle_type=str(payload.get("bundle_type") or "second_brain"),
        max_bundle_bytes=max_bundle_bytes,
        created_by="context-publisher",
    )
    reading_requested = payload.get("ai_reading") is True or ai_reading_enabled_from_env()
    if reading_requested:
        try:
            publication["ai_reading"] = build_bundle_reading(publication)
        except Exception as exc:
            print(f"ai_bundle_reading_failed: {type(exc).__name__}: {exc}")
            publication["ai_reading"] = failed_bundle_reading(exc)
    else:
        publication["ai_reading"] = disabled_bundle_reading()
    publication["bundle"]["ai_reading"] = publication["ai_reading"]
    write_enabled = _request_write_enabled(payload)
    write = write_context_publication(
        publication,
        client=client if write_enabled else _NoopClient(),
        write_enabled=write_enabled,
    )
    return {
        "service": "context-publisher",
        "write_requested": payload.get("write") is True,
        "write_enabled": write_enabled,
        "request_write_enabled": os.environ.get("REQUEST_WRITE_ENABLED", "false").lower() == "true",
        "bundle": {
            "bundle_id": publication["bundle"]["bundle_id"],
            "bundle_type": publication["bundle"]["bundle_type"],
            "approval_status": publication["bundle"]["approval_status"],
            "requires_human_approval": publication["bundle"]["requires_human_approval"],
            "source_file_count": len(publication["bundle"]["source_file_ids"]),
            "actual_bundle_bytes": publication["bundle"]["actual_bundle_bytes"],
        },
        "counts": publication["counts"],
        "ai_reading": {
            "status": publication["ai_reading"].get("status"),
            "provider_id": publication["ai_reading"].get("provider_id"),
            "model_id": publication["ai_reading"].get("model_id"),
        },
        "write": write,
    }


def _request_write_enabled(payload: dict[str, Any]) -> bool:
    if write_enabled_from_env():
        return True
    request_write_allowed = os.environ.get("REQUEST_WRITE_ENABLED", "false").lower() == "true"
    return request_write_allowed and payload.get("write") is True


def _bounded_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return minimum
    return max(minimum, min(parsed, maximum))


def main() -> int:
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), ContextPublisherHandler)
    print(f"context-publisher listening on port {port}")
    server.serve_forever()
    return 0


class _NoopClient:
    def collection(self, collection_name: str) -> Any:
        raise RuntimeError(f"Noop Firestore client cannot write collection {collection_name}")


if __name__ == "__main__":
    raise SystemExit(main())
