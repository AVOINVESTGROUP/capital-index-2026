from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from content_extractor.extraction import extract_from_policy_payload
from content_extractor.plain_text_reader import decode_text_payload, is_plain_text_file
from content_extractor.sheets_reader import extract_sheet_text, make_sheet_result

DOCS_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "docs"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _decision(file_id: str, mime_type: str, name: str) -> dict[str, Any]:
    return {
        "decision_id": f"policy_{file_id}",
        "source_event_id": "evt_test",
        "source_load_id": "metadata_test",
        "trace_id": "trace_test",
        "idempotency_key": "idem_test",
        "file_id": file_id,
        "name": name,
        "mime_type": mime_type,
        "gcp_project_id": "capital-index-2026",
        "project_id": "capital_index",
        "source_registry_id": "drive_event_test",
        "policy_id": "folder_policies/drive_event_test",
        "sensitivity_class": "PUBLIC_INTERNAL",
        "allowed_actions": ["read_content"],
        "denied_actions": [],
        "review_required": False,
    }


class FakeExecute:
    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def execute(self) -> Any:
        return self.payload


class FakeDocsResource:
    def __init__(self, docs: dict[str, dict[str, Any]]) -> None:
        self.docs = docs

    def get(self, **kwargs: Any) -> FakeExecute:
        return FakeExecute(self.docs[kwargs["documentId"]])


class FakeDocsService:
    def __init__(self, docs: dict[str, dict[str, Any]] | None = None) -> None:
        self.docs = docs or {}

    def documents(self) -> FakeDocsResource:
        return FakeDocsResource(self.docs)


class FakeSheetsResource:
    def __init__(self, sheets: dict[str, dict[str, Any]]) -> None:
        self.sheets = sheets

    def get(self, **kwargs: Any) -> FakeExecute:
        return FakeExecute(self.sheets[kwargs["spreadsheetId"]])


class FakeSheetsService:
    def __init__(self, sheets: dict[str, dict[str, Any]]) -> None:
        self.sheets = sheets

    def spreadsheets(self) -> FakeSheetsResource:
        return FakeSheetsResource(self.sheets)


class FakeDriveFilesResource:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files

    def get_media(self, **kwargs: Any) -> FakeExecute:
        return FakeExecute(self.files[kwargs["fileId"]])


class FakeDriveService:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.file_payloads = files

    def files(self) -> FakeDriveFilesResource:
        return FakeDriveFilesResource(self.file_payloads)


class MultiFormatExtractionTest(unittest.TestCase):
    def test_sheet_response_renders_structured_rows(self) -> None:
        sheet = _load(DOCS_FIXTURES / "sheet_response_20260527.json")
        text = extract_sheet_text(sheet)

        self.assertIn("Sheet: Deals", text)
        self.assertIn("Columns: Project | Client | Amount | Status", text)
        self.assertIn("Row 1: Project: Integra Motors", text)
        self.assertIn("Amount: 120000", text)

    def test_make_sheet_result_uses_spreadsheet_title(self) -> None:
        plan = _decision("sheet_test_001", "application/vnd.google-apps.spreadsheet", "Deals")
        plan.update(
            {
                "plan_id": "extract_test",
                "text_only": True,
                "embedding_allowed": False,
                "vault_publish_allowed": False,
                "ai_context_allowed": False,
            }
        )
        result = make_sheet_result(plan, _load(DOCS_FIXTURES / "sheet_response_20260527.json"))

        self.assertEqual(result["doc_title"], "CAPITAL deals tracker")
        self.assertEqual(result["next_action"], "classify")

    def test_markdown_file_is_plain_text_source(self) -> None:
        self.assertTrue(is_plain_text_file({"mime_type": "text/markdown", "name": "README.md"}))
        self.assertTrue(is_plain_text_file({"mime_type": "application/octet-stream", "name": "project.md"}))

    def test_decode_text_payload_accepts_utf8_bytes(self) -> None:
        self.assertEqual(decode_text_payload("# Проект".encode("utf-8")), "# Проект")

    def test_extract_payload_supports_sheets_and_markdown(self) -> None:
        payload = {
            "policy_decisions": [
                _decision("sheet_test_001", "application/vnd.google-apps.spreadsheet", "Deals"),
                _decision("md_test_001", "text/markdown", "README.md"),
            ]
        }
        result = extract_from_policy_payload(
            payload,
            batch_ref="request://body",
            docs_service=FakeDocsService(),
            sheets_service=FakeSheetsService(
                {"sheet_test_001": _load(DOCS_FIXTURES / "sheet_response_20260527.json")}
            ),
            drive_service=FakeDriveService(
                {"md_test_001": b"# Project\n\n- status: active\n- amount: 120000"}
            ),
            docs_read_enabled=False,
            sheets_read_enabled=True,
            drive_read_enabled=True,
        )

        self.assertEqual(result["counts"]["extracted_text"], 2)
        self.assertIn("Sheet: Deals", result["extracted_text"][0]["text"])
        self.assertIn("# Project", result["extracted_text"][1]["text"])
        self.assertEqual(result["counts"]["review_required"], 0)


if __name__ == "__main__":
    unittest.main()
