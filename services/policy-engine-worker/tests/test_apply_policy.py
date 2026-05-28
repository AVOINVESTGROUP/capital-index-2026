from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from policy_engine.decision import apply_policy_batch, apply_policy_payload, decide_file_policy


class ApplyPolicyTest(unittest.TestCase):
    def test_drive_event_test_gets_public_internal_policy(self) -> None:
        fixture = (
            REPO_ROOT
            / "tests"
            / "fixtures"
            / "drive-events"
            / "file_metadata_probe_20260526T105738Z.json"
        )

        result = apply_policy_batch(fixture)

        self.assertEqual(result["schema_version"], "capital.policy_decision_batch.v1")
        self.assertEqual(result["counts"]["input_file_upserts"], 1)
        self.assertEqual(result["counts"]["policy_decisions"], 1)
        self.assertEqual(result["counts"]["review_required"], 0)

        decision = result["policy_decisions"][0]
        self.assertEqual(decision["sensitivity_class"], "PUBLIC_INTERNAL")
        self.assertEqual(decision["project_id"], "capital_index")
        self.assertEqual(decision["gcp_project_id"], "capital-index-2026")
        self.assertEqual(decision["source_registry_id"], "drive_event_test")
        self.assertEqual(decision["mime_type"], "application/vnd.google-apps.document")
        self.assertEqual(decision["name"], "drive-probe-test-001")
        self.assertIn("read_metadata", decision["allowed_actions"])
        self.assertIn("read_content", decision["allowed_actions"])
        self.assertIn("embed", decision["denied_actions"])
        self.assertIn("publish_to_vault", decision["denied_actions"])
        self.assertIn("include_in_ai_context", decision["denied_actions"])
        self.assertFalse(decision["review_required"])
        self.assertEqual(decision["next_action"], "content_extraction_candidate")
        self.assertNotIn("\\", result["input_batch_ref"])
        self.assertNotIn("\\", decision["raw_metadata_ref"])

    def test_unknown_source_uses_default_locked_policy(self) -> None:
        upsert = {
            "load_id": "metadata_test",
            "source_event_id": "evt_test",
            "trace_id": "trace_test",
            "idempotency_key": "idem_test",
            "review_required": False,
            "file": {
                "file_id": "file_test",
                "gcp_project_id": "capital-index-2026",
                "project_id": "capital_index",
                "source_registry_id": "unknown_source",
            },
        }

        decision = decide_file_policy(copy.deepcopy(upsert), batch_ref="fixture.json", index=0)

        self.assertEqual(decision["sensitivity_class"], "UNCLASSIFIED_REVIEW_REQUIRED")
        self.assertEqual(decision["allowed_actions"], ["read_metadata"])
        self.assertIn("read_content", decision["denied_actions"])
        self.assertTrue(decision["review_required"])
        self.assertEqual(decision["review_reason"], "unknown_source_registry")

    def test_decision_id_is_deterministic(self) -> None:
        fixture = (
            REPO_ROOT
            / "tests"
            / "fixtures"
            / "drive-events"
            / "file_metadata_probe_20260526T105738Z.json"
        )

        first = apply_policy_batch(fixture)
        second = apply_policy_batch(fixture)

        self.assertEqual(
            first["policy_decisions"][0]["decision_id"],
            second["policy_decisions"][0]["decision_id"],
        )

    def test_payload_loader_uses_request_ref(self) -> None:
        fixture = (
            REPO_ROOT
            / "tests"
            / "fixtures"
            / "drive-events"
            / "file_metadata_probe_20260526T105738Z.json"
        )
        payload = json.loads(fixture.read_text(encoding="utf-8"))

        result = apply_policy_payload(payload, batch_ref="request://body")

        self.assertEqual(result["input_batch_ref"], "request://body")
        self.assertEqual(result["policy_decisions"][0]["raw_metadata_ref"], "request://body#/file_upserts/0")


if __name__ == "__main__":
    unittest.main()
