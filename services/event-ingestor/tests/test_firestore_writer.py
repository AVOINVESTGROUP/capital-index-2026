from __future__ import annotations

import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from event_ingestor.drive_changes import normalize_probe_fixture
from event_ingestor.firestore_writer import write_event_batch


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


class FirestoreWriterTest(unittest.TestCase):
    def _batch(self) -> dict:
        fixture = REPO_ROOT / "tests" / "fixtures" / "drive-events" / "probe_20260526T105738Z.json"
        return normalize_probe_fixture(fixture)

    def test_write_disabled_does_not_call_firestore(self) -> None:
        client = FakeClient()
        result = write_event_batch(self._batch(), client=client, write_enabled=False)

        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["attempted"], 0)
        self.assertEqual(result["would_write"], 1)
        self.assertEqual(client.collections, {})

    def test_write_enabled_writes_events_with_merge(self) -> None:
        client = FakeClient()
        result = write_event_batch(self._batch(), client=client, write_enabled=True)

        self.assertEqual(result["status"], "written")
        self.assertEqual(result["attempted"], 1)
        self.assertEqual(result["written"], 1)

        calls = client.collections["events"].calls
        self.assertEqual(len(calls), 1)
        document_id, call = calls[0]
        self.assertTrue(document_id.startswith("evt_"))
        self.assertTrue(call["merge"])
        self.assertEqual(call["data"]["firestore_schema_version"], "capital.events.v1")
        self.assertEqual(call["data"]["write_source"], "event-ingestor")


if __name__ == "__main__":
    unittest.main()
