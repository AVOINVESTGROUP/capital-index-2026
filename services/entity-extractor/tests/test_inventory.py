from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from entity_extractor.inventory import build_entity_input_from_firestore


class FakeSnapshot:
    def __init__(self, document_id: str, data: dict[str, Any]) -> None:
        self.id = document_id
        self._data = data

    def to_dict(self) -> dict[str, Any]:
        return self._data


class FakeDocument:
    def __init__(self, snapshot: FakeSnapshot | None) -> None:
        self.snapshot = snapshot

    def get(self) -> FakeSnapshot:
        return self.snapshot or FakeSnapshot("", {})


class FakeCollection:
    def __init__(self, snapshots: list[FakeSnapshot], by_id: dict[str, FakeSnapshot] | None = None) -> None:
        self.snapshots = snapshots
        self.by_id = by_id or {}
        self.limit_count = 1000

    def limit(self, count: int) -> "FakeCollection":
        self.limit_count = count
        return self

    def stream(self) -> list[FakeSnapshot]:
        return self.snapshots[: self.limit_count]

    def document(self, document_id: str) -> FakeDocument:
        return FakeDocument(self.by_id.get(document_id))


class FakeClient:
    def __init__(self) -> None:
        self.extracted = [
            FakeSnapshot(
                "file_1",
                {
                    "file_id": "file_1",
                    "text": "Capital Index source.",
                    "char_count": 21,
                    "source_decision_id": "policy_1",
                },
            )
        ]
        self.files = {
            "file_1": FakeSnapshot(
                "file_1",
                {
                    "file_id": "file_1",
                    "project_id": "capital_index",
                    "source_status": "active",
                    "index_eligible": True,
                    "human_block": False,
                },
            )
        }

    def collection(self, collection_name: str) -> FakeCollection:
        if collection_name == "extracted_text":
            return FakeCollection(self.extracted)
        if collection_name == "files":
            return FakeCollection([], self.files)
        raise AssertionError(collection_name)


class InventoryTest(unittest.TestCase):
    def test_build_entity_input_joins_extracted_text_and_files(self) -> None:
        result = build_entity_input_from_firestore(client=FakeClient(), limit=10)

        self.assertEqual(len(result["extracted_batch"]["extracted_text"]), 1)
        self.assertIn("file_1", result["file_records_by_id"])
        self.assertEqual(result["file_records_by_id"]["file_1"]["source_status"], "active")


if __name__ == "__main__":
    unittest.main()
