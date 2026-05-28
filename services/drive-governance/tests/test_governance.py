from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from drive_governance.governance import evaluate_inventory

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "drive-governance"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class DriveGovernanceTest(unittest.TestCase):
    def test_fixture_generates_expected_cleanup_queue(self) -> None:
        result = evaluate_inventory(_load("file_inventory_governance_mvp.json"))
        expected = _load("expected_cleanup_queue_governance_mvp.json")

        self.assertEqual(result["cleanup_queue"], expected["cleanup_queue"])

    def test_fixture_generates_expected_duplicate_clusters(self) -> None:
        result = evaluate_inventory(_load("file_inventory_governance_mvp.json"))
        expected = _load("expected_file_duplicates_governance_mvp.json")

        self.assertEqual(result["file_duplicates"], expected["file_duplicates"])

    def test_counts_are_reported(self) -> None:
        result = evaluate_inventory(_load("file_inventory_governance_mvp.json"))

        self.assertEqual(result["counts"]["input_files"], 6)
        self.assertEqual(result["counts"]["cleanup_queue"], 4)
        self.assertEqual(result["counts"]["file_duplicates"], 1)

    def test_no_drive_mutation_is_emitted(self) -> None:
        result = evaluate_inventory(_load("file_inventory_governance_mvp.json"))

        for item in result["cleanup_queue"]:
            self.assertTrue(item["human_approval_required"])
            self.assertEqual(item["status"], "open")


if __name__ == "__main__":
    unittest.main()
