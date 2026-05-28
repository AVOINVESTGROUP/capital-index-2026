from __future__ import annotations

import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from metadata_loader.drive_metadata import load_metadata_batch
from metadata_loader.firestore_writer import write_metadata_batch


class FakeDocument:
    def __init__(
        self,
        document_id: str,
        calls: list[tuple[str, dict]],
        existing: dict | None = None,
    ) -> None:
        self.document_id = document_id
        self.calls = calls
        self.existing = existing or {}

    def get(self) -> "FakeSnapshot":
        return FakeSnapshot(self.existing)

    def set(self, data: dict, merge: bool = False) -> None:
        self.calls.append((self.document_id, {"data": data, "merge": merge}))


class FakeSnapshot:
    exists = True

    def __init__(self, data: dict) -> None:
        self.data = data

    def to_dict(self) -> dict:
        return self.data


class FakeCollection:
    def __init__(self, existing_by_id: dict[str, dict] | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.existing_by_id = existing_by_id or {}

    def document(self, document_id: str) -> FakeDocument:
        return FakeDocument(document_id, self.calls, self.existing_by_id.get(document_id))


class FakeClient:
    def __init__(self, existing_by_collection: dict[str, dict[str, dict]] | None = None) -> None:
        self.collections: dict[str, FakeCollection] = {}
        self.existing_by_collection = existing_by_collection or {}

    def collection(self, collection_name: str) -> FakeCollection:
        collection = self.collections.setdefault(
            collection_name,
            FakeCollection(self.existing_by_collection.get(collection_name)),
        )
        return collection


class MetadataFirestoreWriterTest(unittest.TestCase):
    def _batch(self) -> dict:
        fixture = (
            REPO_ROOT
            / "tests"
            / "fixtures"
            / "drive-events"
            / "normalized_probe_20260526T105738Z.json"
        )
        return load_metadata_batch(fixture)

    def test_write_disabled_does_not_call_firestore(self) -> None:
        client = FakeClient()
        result = write_metadata_batch(self._batch(), client=client, write_enabled=False)

        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["attempted"], 0)
        self.assertEqual(result["would_write"], 1)
        self.assertEqual(client.collections, {})

    def test_write_enabled_writes_files_with_merge(self) -> None:
        client = FakeClient()
        result = write_metadata_batch(self._batch(), client=client, write_enabled=True)

        self.assertEqual(result["status"], "written")
        self.assertEqual(result["attempted"], 1)
        self.assertEqual(result["written"], 1)

        calls = client.collections["files"].calls
        self.assertEqual(len(calls), 1)
        document_id, call = calls[0]
        self.assertEqual(document_id, "1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM")
        self.assertTrue(call["merge"])
        self.assertEqual(call["data"]["firestore_schema_version"], "capital.files.v1")
        self.assertEqual(call["data"]["write_source"], "metadata-loader")
        self.assertEqual(call["data"]["project_id"], "capital_index")
        self.assertEqual(call["data"]["source_status"], "needs_human_review")
        self.assertFalse(call["data"]["index_eligible"])
        self.assertFalse(call["data"]["human_block"])

    def test_write_preserves_existing_source_quality(self) -> None:
        file_id = "1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM"
        client = FakeClient(
            {
                "files": {
                    file_id: {
                        "source_status": "active",
                        "index_eligible": True,
                        "human_block": False,
                    }
                }
            }
        )
        write_metadata_batch(self._batch(), client=client, write_enabled=True)

        call = client.collections["files"].calls[0][1]
        self.assertEqual(call["data"]["source_status"], "active")
        self.assertTrue(call["data"]["index_eligible"])
        self.assertFalse(call["data"]["human_block"])


if __name__ == "__main__":
    unittest.main()
