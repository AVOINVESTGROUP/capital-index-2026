"""Cloud Run HTTP entrypoint for entity-extractor."""

from __future__ import annotations

import json
import os
import requests
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from entity_extractor.ai_provider import ai_provider_enabled_from_env, configured_provider_from_env, provider_from_env
from entity_extractor.firestore_writer import (
    firestore_client,
    write_enabled_from_env,
    write_entity_extraction_batch,
)
from entity_extractor.inventory import build_entity_input_from_firestore
from entity_extractor.sheet_classifier import classify_sheet_row
from entity_extractor.worker import build_entity_extraction_batch


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


class EntityExtractorHandler(BaseHTTPRequestHandler):
    server_version = "capital-entity-extractor/0.1"

    def do_GET(self) -> None:
        if self.path == "/healthz":
            _json_response(self, HTTPStatus.OK, {"status": "ok", "service": "entity-extractor"})
            return
        _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path == "/classify-sheet-row":
            self._classify_sheet_row()
            return

        if self.path != "/extract-entities":
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        auth_error = _authorize_operator_request(self.headers.get("Authorization", ""))
        if auth_error:
            _json_response(self, HTTPStatus.UNAUTHORIZED, auth_error)
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
        if payload.get("extracted_batch"):
            entity_input = {
                "extracted_batch": payload.get("extracted_batch") or {},
                "file_records_by_id": payload.get("file_records_by_id") or {},
                "batch_ref": payload.get("batch_ref") or "request://body",
            }
            input_source = "request_body"
        else:
            entity_input = build_entity_input_from_firestore(
                client=client,
                limit=_limit(payload),
                batch_ref="firestore://extracted_text",
            )
            input_source = "firestore"

        provider = provider_from_env()
        result = build_entity_extraction_batch(
            entity_input["extracted_batch"],
            entity_input["file_records_by_id"],
            batch_ref=entity_input["batch_ref"],
            ai_responses_by_file_id=payload.get("ai_responses_by_file_id") or {},
            ai_response_provider=provider.extract if ai_provider_enabled_from_env() else None,
            provider_id=payload.get("provider_id") or provider.provider_id,
            model_id=payload.get("model_id") or provider.model_id,
        )
        result["input_source"] = input_source
        result["ai_provider_enabled"] = ai_provider_enabled_from_env()
        write_enabled = _request_write_enabled(payload)
        result["write_requested"] = bool(payload.get("write"))
        result["request_write_enabled"] = os.environ.get("REQUEST_WRITE_ENABLED", "false").lower() == "true"
        result["write"] = write_entity_extraction_batch(
            result,
            client=client if write_enabled else _NoopClient(),
            write_enabled=write_enabled,
        )
        _json_response(self, HTTPStatus.OK, result)

    def _classify_sheet_row(self) -> None:
        try:
            payload = _request_json(self)
        except (ValueError, json.JSONDecodeError) as exc:
            print(f"invalid_json: {exc}")
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "invalid_json", "detail": str(exc)})
            return

        if not _sheet_classifier_enabled_from_env():
            _json_response(
                self,
                HTTPStatus.SERVICE_UNAVAILABLE,
                {
                    "error": "sheet_classifier_disabled",
                    "detail": "SHEET_CLASSIFIER_ENABLED must be true for /classify-sheet-row.",
                },
            )
            return

        auth_error = _authorize_sheet_classifier_request(self.headers.get("Authorization", ""))
        if auth_error:
            _json_response(self, HTTPStatus.UNAUTHORIZED, auth_error)
            return

        try:
            provider = configured_provider_from_env()
            result = classify_sheet_row(payload.get("row") or payload, provider=provider)
        except Exception as exc:  # pragma: no cover - Cloud Run logs need exact upstream failure.
            print(f"sheet_classification_failed: {type(exc).__name__}: {exc}")
            _json_response(
                self,
                HTTPStatus.BAD_GATEWAY,
                {"error": "sheet_classification_failed", "detail": str(exc)},
            )
            return

        _json_response(
            self,
            HTTPStatus.OK,
            {
                "schema_version": "capital.sheet_file_classification.v1",
                "provider_id": provider.provider_id,
                "model_id": provider.model_id,
                "classification": result,
            },
        )

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def _limit(payload: dict[str, Any]) -> int:
    value = payload["limit"] if "limit" in payload else os.environ.get("EXTRACTION_LIMIT", "100")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 100
    return max(1, min(parsed, 500))


def _request_write_enabled(payload: dict[str, Any]) -> bool:
    if write_enabled_from_env():
        return True
    request_write_allowed = os.environ.get("REQUEST_WRITE_ENABLED", "false").lower() == "true"
    return request_write_allowed and payload.get("write") is True


def _sheet_classifier_enabled_from_env() -> bool:
    return os.environ.get("SHEET_CLASSIFIER_ENABLED", "false").lower() == "true"


def _authorize_sheet_classifier_request(authorization_header: str) -> dict[str, str] | None:
    return _authorize_operator_request(authorization_header)


def _authorize_operator_request(authorization_header: str) -> dict[str, str] | None:
    allowed = _allowed_operator_emails()
    if not allowed:
        return {
            "error": "operator_allowlist_missing",
            "detail": "HTTP_ALLOWED_EMAILS or SHEET_CLASSIFIER_ALLOWED_EMAILS must be configured.",
        }

    if not authorization_header.startswith("Bearer "):
        return {"error": "missing_bearer_token"}

    token = authorization_header.removeprefix("Bearer ").strip()
    token_info_error: dict[str, str] | None = None
    for params in _tokeninfo_param_candidates(token):
        try:
            response = requests.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params=params,
                timeout=10,
            )
        except requests.RequestException as exc:
            return {"error": "token_validation_failed", "detail": str(exc)}

        if not response.ok:
            token_info_error = {"error": "invalid_bearer_token", "detail": response.text[:500]}
            continue

        token_info = response.json()
        email = str(token_info.get("email") or "").lower()
        if email in allowed:
            return None

        return {"error": "operator_not_allowed", "email": email}

    return token_info_error or {"error": "invalid_bearer_token"}


def _tokeninfo_param_candidates(token: str) -> list[dict[str, str]]:
    if token.count(".") == 2:
        return [{"id_token": token}, {"access_token": token}]
    return [{"access_token": token}, {"id_token": token}]


def _allowed_operator_emails() -> set[str]:
    raw = os.environ.get("HTTP_ALLOWED_EMAILS") or os.environ.get("SHEET_CLASSIFIER_ALLOWED_EMAILS", "")
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def main() -> int:
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), EntityExtractorHandler)
    print(f"entity-extractor listening on port {port}")
    server.serve_forever()
    return 0


class _NoopClient:
    def collection(self, collection_name: str) -> Any:
        raise RuntimeError(f"Noop Firestore client cannot write collection {collection_name}")


if __name__ == "__main__":
    raise SystemExit(main())
