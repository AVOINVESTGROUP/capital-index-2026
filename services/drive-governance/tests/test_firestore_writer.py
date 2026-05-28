from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from drive_governance.governance import evaluate_inventory
from drive_governance.firestore_writer import write_governance_batch

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "drive-governance"


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


def _batch() -> dict:
    inventory = json.loads((FIXTURES / "file_inventory_governance_mvp.json").read_text(encoding="utf-8"))
    return evaluate_inventory(inventory)


class FirestoreWriterTest(unittest.TestCase):
    def test_disabled_does_not_call_firestore(self) -> None:
        client = FakeClient()
        result = write_governance_batch(_batch(), client=client, write_enabled=False)

        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["would_write_cleanup_queue"], 4)
        self.assertEqual(result["would_write_file_duplicates"], 1)
        self.assertEqual(client.collections, {})

    def test_enabled_writes_cleanup_and_duplicates(self) -> None:
        client = FakeClient()
        result = write_governance_batch(_batch(), client=client, write_enabled=True)

        self.assertEqual(result["status"], "written")
        self.assertEqual(result["written_cleanup_queue"], 4)
        self.assertEqual(result["written_file_duplicates"], 1)

        cleanup_calls = client.collections["cleanup_queue"].calls
        duplicate_calls = client.collections["file_duplicates"].calls
        self.assertEqual(len(cleanup_calls), 4)
        self.assertEqual(len(duplicate_calls), 1)
        self.assertTrue(cleanup_calls[0][0].startswith("cleanup_"))
        self.assertTrue(duplicate_calls[0][0].startswith("dup_"))
        self.assertTrue(cleanup_calls[0][1]["merge"])
        self.assertTrue(duplicate_calls[0][1]["merge"])

    def test_missing_document_id_fails_before_partial_write(self) -> None:
        client = FakeClient()
        batch = _batch()
        batch["cleanup_queue"][0] = {**batch["cleanup_queue"][0], "cleanup_id": ""}

        with self.assertRaises(ValueError):
            write_governance_batch(batch, client=client, write_enabled=True)


if __name__ == "__main__":
    unittest.main()
