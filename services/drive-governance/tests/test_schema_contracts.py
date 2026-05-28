from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "drive-governance"

CLEANUP_ID = re.compile(r"^cleanup_[a-f0-9]{24}$")
DUPLICATE_ID = re.compile(r"^dup_[a-f0-9]{24}$")

CLEANUP_STATUSES = {
    "candidate_duplicate",
    "candidate_stale",
    "candidate_empty",
    "candidate_archive",
    "needs_human_review",
}
CLEANUP_REASONS = {
    "duplicate",
    "near_duplicate",
    "stale",
    "empty",
    "orphaned",
    "version_superseded",
    "unknown_project",
    "temporary_name",
}
CLEANUP_ACTIONS = {
    "keep_active",
    "mark_duplicate",
    "archive",
    "move_to_review",
    "do_not_index",
    "needs_review",
}


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class SchemaContractsTest(unittest.TestCase):
    def test_cleanup_queue_fixture_matches_contract(self) -> None:
        payload = _load("expected_cleanup_queue_governance_mvp.json")

        for item in payload["cleanup_queue"]:
            self.assertEqual(item["schema_version"], "capital.cleanup_queue.v1")
            self.assertRegex(item["cleanup_id"], CLEANUP_ID)
            self.assertTrue(item["file_id"])
            self.assertIn(item["source_status"], CLEANUP_STATUSES)
            self.assertIn(item["reason"], CLEANUP_REASONS)
            self.assertIn(item["recommended_action"], CLEANUP_ACTIONS)
            self.assertGreaterEqual(item["confidence"], 0)
            self.assertLessEqual(item["confidence"], 1)
            self.assertTrue(item["human_approval_required"])
            self.assertEqual(item["status"], "open")

            evidence = item["evidence"]
            self.assertIsInstance(evidence["signals"], list)
            self.assertIn("matched_file_ids", evidence)
            self.assertIn("age_days", evidence)
            self.assertIn("modified_at", evidence)
            self.assertIn("size", evidence)

    def test_duplicate_fixture_matches_contract(self) -> None:
        payload = _load("expected_file_duplicates_governance_mvp.json")

        for item in payload["file_duplicates"]:
            self.assertEqual(item["schema_version"], "capital.file_duplicate.v1")
            self.assertRegex(item["cluster_id"], DUPLICATE_ID)
            self.assertIn(
                item["cluster_type"],
                {"exact_duplicate", "near_duplicate", "version_family", "template_reuse", "evidence_copy"},
            )
            self.assertGreaterEqual(item["confidence"], 0)
            self.assertLessEqual(item["confidence"], 1)
            self.assertGreaterEqual(len(item["member_file_ids"]), 1)
            self.assertIn(item["action"], {"none", "archive_suggested", "review_required"})

            evidence = item["evidence"]
            self.assertIsInstance(evidence["signals"], list)
            self.assertIn("hash_match", evidence)
            self.assertIn("same_parent", evidence)
            self.assertIn("newest_file_id", evidence)

    def test_inventory_fixture_has_required_file_fields(self) -> None:
        payload = _load("file_inventory_governance_mvp.json")

        for item in payload["files"]:
            self.assertTrue(item["file_id"])
            self.assertTrue(item["name"])
            self.assertTrue(item["mime_type"])
            self.assertIsInstance(item["parents"], list)
            self.assertIn("project_id", item)
            self.assertIn("source_registry_id", item)
            self.assertIn("text_stats", item)


if __name__ == "__main__":
    unittest.main()
