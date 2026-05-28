from __future__ import annotations

import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from event_ingestor.drive_changes import normalize_probe_fixture, normalize_probe_payload


class NormalizeDriveChangesTest(unittest.TestCase):
    def test_probe_fixture_becomes_one_normalized_event(self) -> None:
        fixture = REPO_ROOT / "tests" / "fixtures" / "drive-events" / "probe_20260526T105738Z.json"

        result = normalize_probe_fixture(fixture)

        self.assertEqual(result["schema_version"], "capital.event_batch.v1")
        self.assertEqual(result["counts"]["input_changes"], 5)
        self.assertEqual(result["counts"]["folder_changes"], 1)
        self.assertEqual(result["counts"]["events"], 1)
        self.assertEqual(result["counts"]["review_required"], 0)

        event = result["events"][0]
        self.assertTrue(event["event_id"].startswith("evt_"))
        self.assertTrue(event["trace_id"].startswith("trace_"))
        self.assertEqual(len(event["idempotency_key"]), 64)
        self.assertEqual(event["source"], "drive_changes")
        self.assertEqual(event["gcp_project_id"], "capital-index-2026")
        self.assertEqual(event["project_id"], "capital_index")
        self.assertEqual(event["source_registry_id"], "drive_event_test")
        self.assertEqual(event["event_type"], "drive.file.changed")
        self.assertEqual(event["source_event_type"], "file")
        self.assertEqual(event["file_id"], "1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM")
        self.assertNotIn("\\", result["fixture_path"])
        self.assertNotIn("\\", event["raw_payload_ref"])
        self.assertEqual(event["file"]["name"], "drive-probe-test-001")
        self.assertEqual(event["next_action"], "load_metadata")
        self.assertFalse(event["review_required"])

    def test_normalization_is_deterministic(self) -> None:
        fixture = REPO_ROOT / "tests" / "fixtures" / "drive-events" / "probe_20260526T105738Z.json"

        first = normalize_probe_fixture(fixture)
        second = normalize_probe_fixture(fixture)

        self.assertEqual(first["events"][0]["event_id"], second["events"][0]["event_id"])
        self.assertEqual(first["events"][0]["idempotency_key"], second["events"][0]["idempotency_key"])

    def test_payload_normalization_uses_request_ref(self) -> None:
        fixture = REPO_ROOT / "tests" / "fixtures" / "drive-events" / "probe_20260526T105738Z.json"
        payload = __import__("json").loads(fixture.read_text(encoding="utf-8"))

        result = normalize_probe_payload(payload, fixture_ref="request://body")

        self.assertEqual(result["fixture_path"], "request://body")
        self.assertEqual(result["events"][0]["raw_payload_ref"], "request://body#/folder_changes/0")


if __name__ == "__main__":
    unittest.main()
