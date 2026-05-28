from __future__ import annotations

import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

import json

from metadata_loader.drive_metadata import load_metadata_batch, load_metadata_payload


class LoadDriveMetadataTest(unittest.TestCase):
    def test_normalized_event_becomes_file_upsert(self) -> None:
        fixture = (
            REPO_ROOT
            / "tests"
            / "fixtures"
            / "drive-events"
            / "normalized_probe_20260526T105738Z.json"
        )

        result = load_metadata_batch(fixture)

        self.assertEqual(result["schema_version"], "capital.file_metadata_batch.v1")
        self.assertEqual(result["counts"]["input_events"], 1)
        self.assertEqual(result["counts"]["file_upserts"], 1)
        self.assertEqual(result["counts"]["review_required"], 0)

        upsert = result["file_upserts"][0]
        self.assertEqual(upsert["operation"], "upsert")
        self.assertEqual(upsert["metadata_status"], "base_loaded")
        self.assertEqual(upsert["authoritative_refetch_status"], "pending")
        self.assertEqual(upsert["next_action"], "policy_check")
        self.assertFalse(upsert["review_required"])
        self.assertNotIn("\\", result["input_batch_ref"])
        self.assertNotIn("\\", upsert["raw_event_ref"])

        file_payload = upsert["file"]
        self.assertEqual(file_payload["file_id"], "1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM")
        self.assertEqual(file_payload["name"], "drive-probe-test-001")
        self.assertEqual(file_payload["mime_type"], "application/vnd.google-apps.document")
        self.assertEqual(file_payload["gcp_project_id"], "capital-index-2026")
        self.assertEqual(file_payload["project_id"], "capital_index")
        self.assertEqual(file_payload["source_registry_id"], "drive_event_test")

        self.assertIsNone(upsert["authoritative_fields"]["owners"])
        self.assertIsNone(upsert["authoritative_fields"]["head_revision_id"])

    def test_metadata_load_id_is_deterministic(self) -> None:
        fixture = (
            REPO_ROOT
            / "tests"
            / "fixtures"
            / "drive-events"
            / "normalized_probe_20260526T105738Z.json"
        )

        first = load_metadata_batch(fixture)
        second = load_metadata_batch(fixture)

        self.assertEqual(first["file_upserts"][0]["load_id"], second["file_upserts"][0]["load_id"])

    def test_payload_loader_uses_request_ref(self) -> None:
        fixture = (
            REPO_ROOT
            / "tests"
            / "fixtures"
            / "drive-events"
            / "normalized_probe_20260526T105738Z.json"
        )
        payload = json.loads(fixture.read_text(encoding="utf-8"))

        result = load_metadata_payload(payload, batch_ref="request://body")

        self.assertEqual(result["input_batch_ref"], "request://body")
        self.assertEqual(result["file_upserts"][0]["raw_event_ref"], "request://body#/events/0")


if __name__ == "__main__":
    unittest.main()
