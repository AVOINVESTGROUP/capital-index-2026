from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from entity_extractor.firestore_writer import write_entity_extraction_batch
from entity_extractor.worker import build_entity_extraction_batch

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "entity-extractor"


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


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _batch() -> dict:
    return build_entity_extraction_batch(
        _load("extracted_text_entity_gate_mvp.json"),
        _load("file_records_entity_gate_mvp.json"),
        batch_ref="fixture://entity_gate",
        ai_responses_by_file_id={"file_active_001": _load("ai_response_entity_extraction_mvp.json")},
        provider_id="fixture",
        model_id="fixture-model",
    )


class FirestoreWriterTest(unittest.TestCase):
    def test_disabled_does_not_call_firestore(self) -> None:
        client = FakeClient()
        result = write_entity_extraction_batch(_batch(), client=client, write_enabled=False)

        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["would_write"], 3)
        self.assertEqual(client.collections, {})

    def test_enabled_writes_entity_extractions(self) -> None:
        client = FakeClient()
        result = write_entity_extraction_batch(_batch(), client=client, write_enabled=True)

        self.assertEqual(result["status"], "written")
        self.assertEqual(result["written"], 3)
        calls = client.collections["entity_extractions"].calls
        self.assertEqual(len(calls), 3)
        self.assertTrue(calls[0][0].startswith("entity_extraction_"))
        self.assertTrue(calls[0][1]["merge"])

    def test_missing_extraction_id_fails_before_write(self) -> None:
        client = FakeClient()
        batch = _batch()
        batch["entity_extractions"][0] = {**batch["entity_extractions"][0], "extraction_id": ""}

        with self.assertRaises(ValueError):
            write_entity_extraction_batch(batch, client=client, write_enabled=True)


if __name__ == "__main__":
    unittest.main()
