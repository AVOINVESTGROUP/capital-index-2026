from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from drive_governance.inventory import build_inventory_from_firestore


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
        self.files = [
            FakeSnapshot(
                "file_1",
                {
                    "name": "Example Doc",
                    "mime_type": "application/vnd.google-apps.document",
                    "parents": ["folder_1"],
                    "modified_time": "2026-05-26T10:00:00Z",
                    "project_id": "capital_index",
                    "source_registry_id": "drive_event_test",
                },
            )
        ]
        self.extracted = {
            "file_1": FakeSnapshot(
                "file_1",
                {
                    "text": "hello world",
                    "char_count": 11,
                    "non_whitespace_char_count": 10,
                },
            )
        }

    def collection(self, collection_name: str) -> FakeCollection:
        if collection_name == "files":
            return FakeCollection(self.files)
        if collection_name == "extracted_text":
            return FakeCollection([], self.extracted)
        raise AssertionError(collection_name)


class InventoryTest(unittest.TestCase):
    def test_build_inventory_joins_files_and_extracted_text(self) -> None:
        inventory = build_inventory_from_firestore(client=FakeClient(), limit=10)

        self.assertEqual(inventory["schema_version"], "capital.drive_governance_inventory.v1")
        self.assertEqual(len(inventory["files"]), 1)
        file_obj = inventory["files"][0]
        self.assertEqual(file_obj["file_id"], "file_1")
        self.assertEqual(file_obj["project_id"], "capital_index")
        self.assertEqual(file_obj["text_stats"]["char_count"], 11)
        self.assertEqual(file_obj["text_stats"]["non_whitespace_char_count"], 10)
        self.assertIsNotNone(file_obj["text_stats"]["text_hash"])


if __name__ == "__main__":
    unittest.main()
