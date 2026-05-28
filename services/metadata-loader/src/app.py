"""Cloud Run HTTP entrypoint for metadata-loader.

This deployment target is write-disabled unless WRITE_ENABLED=true is set.
"""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from metadata_loader.drive_metadata import load_metadata_payload
from metadata_loader.drive_refetch import refetch_authoritative_batch, refetch_enabled_from_env
from metadata_loader.firestore_writer import (
    firestore_client,
    write_enabled_from_env,
    write_metadata_batch,
)
from metadata_loader.job_publisher import (
    policy_topic_from_env,
    publish_enabled_from_env,
    publish_policy_job,
    pubsub_publisher,
)
from metadata_loader.pubsub import decode_pubsub_json, pubsub_message_ref
from metadata_loader.workspace_auth import build_drive_service


def _json_response(handler: BaseHTTPRequestHandler, status: HTTPStatus, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class MetadataLoaderHandler(BaseHTTPRequestHandler):
    server_version = "capital-metadata-loader/0.1"

    def do_GET(self) -> None:
        if self.path == "/healthz":
            _json_response(self, HTTPStatus.OK, {"status": "ok", "service": "metadata-loader"})
            return
        _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path not in {"/load-drive-metadata", "/pubsub/metadata"}:
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            if self.path == "/pubsub/metadata":
                batch_ref = pubsub_message_ref(payload)
                payload = decode_pubsub_json(payload)
            else:
                batch_ref = "request://body"
        except (ValueError, json.JSONDecodeError) as exc:
            print(f"invalid_json: {exc}")
            _json_response(
                self,
                HTTPStatus.BAD_REQUEST,
                {"error": "invalid_json", "detail": str(exc)},
            )
            return

        result = load_metadata_payload(payload, batch_ref=batch_ref)
        if refetch_enabled_from_env():
            result = refetch_authoritative_batch(
                result,
                service=build_drive_service(),
                refetch_enabled=True,
            )
        else:
            result = refetch_authoritative_batch(
                result,
                service=_NoopDriveService(),
                refetch_enabled=False,
            )
        if write_enabled_from_env():
            client = firestore_client(
                os.environ.get("GCP_PROJECT_ID", "capital-index-2026"),
                os.environ.get("FIRESTORE_DATABASE", "(default)"),
            )
            result["write"] = write_metadata_batch(result, client=client, write_enabled=True)
        else:
            result["write"] = write_metadata_batch(result, client=_NoopClient(), write_enabled=False)
        if result["write"]["status"] == "written" and publish_enabled_from_env():
            result["policy_job"] = publish_policy_job(
                result,
                publisher=pubsub_publisher(),
                project_id=os.environ.get("GCP_PROJECT_ID", "capital-index-2026"),
                topic_name=policy_topic_from_env(),
                publish_enabled=True,
            )
        else:
            result["policy_job"] = publish_policy_job(
                result,
                publisher=_NoopPublisher(),
                project_id=os.environ.get("GCP_PROJECT_ID", "capital-index-2026"),
                topic_name=policy_topic_from_env(),
                publish_enabled=False,
            )
        _json_response(self, HTTPStatus.OK, result)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> int:
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), MetadataLoaderHandler)
    print(f"metadata-loader listening on port {port}")
    server.serve_forever()
    return 0


class _NoopClient:
    def collection(self, collection_name: str) -> Any:
        raise RuntimeError(f"Noop Firestore client cannot write collection {collection_name}")


class _NoopDriveService:
    def files(self) -> Any:
        raise RuntimeError("Noop Drive service cannot fetch files")

    def revisions(self) -> Any:
        raise RuntimeError("Noop Drive service cannot fetch revisions")


class _NoopPublisher:
    def topic_path(self, project_id: str, topic_name: str) -> str:
        raise RuntimeError(f"Noop Pub/Sub publisher cannot publish to {project_id}/{topic_name}")

    def publish(self, topic_path: str, data: bytes, **attrs: str) -> Any:
        raise RuntimeError(f"Noop Pub/Sub publisher cannot publish to {topic_path}")


if __name__ == "__main__":
    raise SystemExit(main())
