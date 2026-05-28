from __future__ import annotations

import io
import json
import sys
import unittest
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

import app


class FakeProvider:
    provider_id = "gemini"
    model_id = "gemini-2.5-flash"

    def generate_json(self, *, system: str, user: str) -> dict[str, object]:
        return {
            "project": "Integra Motors Dubai",
            "sub_topic": "CRM",
            "type": "Strategy note",
            "summary_50w": "CRM strategy and sales workflow.",
            "linked_projects": "Integra Motors Dubai",
            "value_score": 4,
            "action": "KEEP",
        }


class FakeHandler:
    def __init__(self, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.headers = {"Content-Length": str(len(body)), "Authorization": "Bearer test-token"}
        self.rfile = io.BytesIO(body)
        self.status: HTTPStatus | None = None
        self.response_headers: dict[str, str] = {}
        self.wfile = io.BytesIO()

    def send_response(self, status: HTTPStatus) -> None:
        self.status = status

    def send_header(self, key: str, value: str) -> None:
        self.response_headers[key] = value

    def end_headers(self) -> None:
        pass


class AppSheetClassifierTest(unittest.TestCase):
    @patch("app._sheet_classifier_enabled_from_env", return_value=True)
    @patch("app._authorize_sheet_classifier_request", return_value=None)
    @patch("app.configured_provider_from_env", return_value=FakeProvider())
    def test_classify_sheet_row_endpoint(self, _provider: object, _auth: object, _enabled: object) -> None:
        handler = FakeHandler({"row": {"file_name": "crm.md", "content": "CRM plan"}})

        app.EntityExtractorHandler._classify_sheet_row(handler)  # type: ignore[arg-type]

        self.assertEqual(handler.status, HTTPStatus.OK)
        payload = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertEqual(payload["classification"]["project"], "Integra Motors Dubai")
        self.assertEqual(payload["provider_id"], "gemini")

    @patch("app._sheet_classifier_enabled_from_env", return_value=False)
    def test_classify_sheet_row_disabled(self, _enabled: object) -> None:
        handler = FakeHandler({"row": {"file_name": "crm.md"}})

        app.EntityExtractorHandler._classify_sheet_row(handler)  # type: ignore[arg-type]

        self.assertEqual(handler.status, HTTPStatus.SERVICE_UNAVAILABLE)


if __name__ == "__main__":
    unittest.main()
