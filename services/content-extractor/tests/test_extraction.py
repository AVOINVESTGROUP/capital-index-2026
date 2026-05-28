from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from content_extractor.extraction import extract_from_policy_payload


class FakeExecute:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def execute(self) -> dict:
        return self.payload


class FakeDocuments:
    def __init__(self, service: "FakeDocsService") -> None:
        self.service = service

    def get(self, **kwargs) -> FakeExecute:
        self.service.calls.append(kwargs)
        return FakeExecute(self.service.doc)


class FakeDocsService:
    def __init__(self, doc: dict) -> None:
        self.doc = doc
        self.calls: list[dict] = []

    def documents(self) -> FakeDocuments:
        return FakeDocuments(self)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ExtractionTest(unittest.TestCase):
    def _policy_payload(self) -> dict:
        return _load(
            REPO_ROOT
            / "tests"
            / "fixtures"
            / "drive-events"
            / "policy_decision_probe_20260526T105738Z.json"
        )

    def _doc(self) -> dict:
        return _load(REPO_ROOT / "tests" / "fixtures" / "docs" / "doc_response_20260526T105738Z.json")

    def test_docs_read_disabled_returns_pending_without_call(self) -> None:
        service = FakeDocsService(self._doc())
        result = extract_from_policy_payload(
            self._policy_payload(),
            batch_ref="request://body",
            docs_service=service,
            docs_read_enabled=False,
        )

        self.assertEqual(result["counts"]["extracted_text"], 1)
        self.assertEqual(result["extracted_text"][0]["next_action"], "pending")
        self.assertEqual(result["extracted_text"][0]["review_reason"], "docs_read_disabled")
        self.assertEqual(service.calls, [])

    def test_docs_read_enabled_extracts_text(self) -> None:
        service = FakeDocsService(self._doc())
        result = extract_from_policy_payload(
            self._policy_payload(),
            batch_ref="request://body",
            docs_service=service,
            docs_read_enabled=True,
        )

        item = result["extracted_text"][0]
        self.assertEqual(item["schema_version"], "capital.extracted_text.v1")
        self.assertEqual(item["file_id"], "1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM")
        self.assertEqual(item["next_action"], "classify")
        self.assertGreater(item["char_count"], 0)
        self.assertFalse(item["embedding_allowed"])
        self.assertEqual(len(service.calls), 1)

    def test_review_policy_does_not_read_doc(self) -> None:
        payload = self._policy_payload()
        payload["policy_decisions"][0]["review_required"] = True
        payload["policy_decisions"][0]["review_reason"] = "manual_review"
        service = FakeDocsService(self._doc())

        result = extract_from_policy_payload(
            payload,
            batch_ref="request://body",
            docs_service=service,
            docs_read_enabled=True,
        )

        self.assertEqual(result["extracted_text"][0]["next_action"], "review_required")
        self.assertEqual(result["extracted_text"][0]["review_reason"], "manual_review")
        self.assertEqual(service.calls, [])


if __name__ == "__main__":
    unittest.main()
