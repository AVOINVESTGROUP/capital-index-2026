from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from content_extractor.extraction import extract_from_policy_payload
from content_extractor.review_queue import write_review_queue_batch
from test_extraction import FakeDocsService


class FakeDocument:
    def __init__(self, document_id: str, calls: list[tuple[str, dict]]) -> None:
        self.document_id = document_id
        self.calls = calls

    def set(self, data: dict, merge: bool = False) -> None:
        self.calls.append((self.document_id, {"data": data, "merge": merge}))


class FakeCollection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def document(self, document_id: str) -> FakeDocument:
        return FakeDocument(document_id, self.calls)


class FakeClient:
    def __init__(self) -> None:
        self.collections: dict[str, FakeCollection] = {}

    def collection(self, collection_name: str) -> FakeCollection:
        collection = self.collections.setdefault(collection_name, FakeCollection())
        return collection


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ReviewQueueTest(unittest.TestCase):
    def _review_batch(self) -> dict:
        policy = _load(REPO_ROOT / "tests" / "fixtures" / "drive-events" / "policy_decision_probe_20260526T105738Z.json")
        doc = _load(REPO_ROOT / "tests" / "fixtures" / "docs" / "doc_response_probe_20260526T105738Z.json")
        return extract_from_policy_payload(
            policy,
            batch_ref="request://body",
            docs_service=FakeDocsService(doc),
            docs_read_enabled=True,
        )

    def _clean_batch(self) -> dict:
        policy = _load(REPO_ROOT / "tests" / "fixtures" / "drive-events" / "policy_decision_probe_20260526T105738Z.json")
        doc = _load(REPO_ROOT / "tests" / "fixtures" / "docs" / "doc_response_20260526T105738Z.json")
        return extract_from_policy_payload(
            policy,
            batch_ref="request://body",
            docs_service=FakeDocsService(doc),
            docs_read_enabled=True,
        )

    def test_disabled_does_not_call_firestore(self) -> None:
        client = FakeClient()
        result = write_review_queue_batch(self._review_batch(), client=client, review_queue_enabled=False)

        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["would_write"], 1)
        self.assertEqual(client.collections, {})

    def test_enabled_writes_review_items(self) -> None:
        client = FakeClient()
        result = write_review_queue_batch(self._review_batch(), client=client, review_queue_enabled=True)

        self.assertEqual(result["status"], "written")
        self.assertEqual(result["written"], 1)
        calls = client.collections["review_queue"].calls
        self.assertEqual(len(calls), 1)
        document_id, call = calls[0]
        self.assertTrue(document_id.startswith("review_"))
        self.assertTrue(call["merge"])
        self.assertEqual(call["data"]["status"], "open")
        self.assertEqual(call["data"]["reason"], "empty_text")

    def test_clean_batch_writes_nothing(self) -> None:
        client = FakeClient()
        result = write_review_queue_batch(self._clean_batch(), client=client, review_queue_enabled=True)

        self.assertEqual(result["written"], 0)
        self.assertEqual(client.collections.get("review_queue").calls if client.collections else [], [])


if __name__ == "__main__":
    unittest.main()
