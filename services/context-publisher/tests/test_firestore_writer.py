import sys
import unittest
from pathlib import Path

SERVICE_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SERVICE_SRC))

from context_publisher.firestore_writer import write_context_publication


class FakeDocument:
    def __init__(self, store, collection, document_id):
        self.store = store
        self.collection = collection
        self.document_id = document_id

    def set(self, data, merge=False):
        self.store[(self.collection, self.document_id)] = {"data": data, "merge": merge}


class FakeCollection:
    def __init__(self, store, name):
        self.store = store
        self.name = name

    def document(self, document_id):
        return FakeDocument(self.store, self.name, document_id)


class FakeClient:
    def __init__(self):
        self.store = {}

    def collection(self, collection_name):
        return FakeCollection(self.store, collection_name)


def publication():
    return {
        "bundle": {"bundle_id": "bundle_1"},
        "vault_projection": {"projection_id": "projection_1"},
        "source_evidence": [{"evidence_id": "evidence_1"}],
        "claims": [{"claim_id": "claim_1"}],
        "entities": [{"entity_id": "entity_1"}],
        "relationships": [{"relationship_id": "relationship_1"}],
        "ai_reading": {"status": "generated", "executive_summary": "Summary"},
        "counts": {
            "evidence": 1,
            "claims": 1,
            "entities": 1,
            "relationships": 1,
        },
    }


class FirestoreWriterTest(unittest.TestCase):
    def test_disabled_write_reports_plan_without_touching_client(self):
        client = FakeClient()
        result = write_context_publication(publication(), client=client, write_enabled=False)

        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["bundle_id"], "bundle_1")
        self.assertEqual(result["would_write"]["claims"], 1)
        self.assertEqual(client.store, {})

    def test_enabled_write_persists_artifacts_and_current_pointers(self):
        client = FakeClient()
        result = write_context_publication(publication(), client=client, write_enabled=True)

        self.assertEqual(result["status"], "written")
        self.assertIn(("source_evidence", "evidence_1"), client.store)
        self.assertIn(("claims", "claim_1"), client.store)
        self.assertIn(("entities", "entity_1"), client.store)
        self.assertIn(("relationships", "relationship_1"), client.store)
        self.assertIn(("context_bundles", "bundle_1"), client.store)
        self.assertIn(("context_bundles", "current"), client.store)
        self.assertIn(("context_bundle_readings", "bundle_1"), client.store)
        self.assertIn(("vault_projections", "projection_1"), client.store)
        self.assertIn(("vault_projections", "current_second_brain"), client.store)
        self.assertTrue(client.store[("claims", "claim_1")]["merge"])


if __name__ == "__main__":
    unittest.main()
