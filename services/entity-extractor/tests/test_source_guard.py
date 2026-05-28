from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from entity_extractor.source_guard import build_entity_candidates, source_gate

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "entity-extractor"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class SourceGuardTest(unittest.TestCase):
    def test_active_and_index_eligible_file_is_allowed(self) -> None:
        result = source_gate({"source_status": "active", "index_eligible": True})

        self.assertTrue(result["allowed"])
        self.assertEqual(result["reason"], "allowed")
        self.assertEqual(result["reasons"], [])

    def test_candidate_duplicate_is_blocked(self) -> None:
        result = source_gate({"source_status": "candidate_duplicate", "index_eligible": False})

        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "blocked_by_drive_governance")
        self.assertIn("source_status_not_active", result["reasons"])
        self.assertIn("index_eligible_not_true", result["reasons"])

    def test_missing_file_record_is_blocked_by_default(self) -> None:
        result = source_gate(None)

        self.assertFalse(result["allowed"])
        self.assertIn("source_status_not_active", result["reasons"])
        self.assertIn("index_eligible_not_true", result["reasons"])

    def test_human_block_overrides_active_file(self) -> None:
        result = source_gate(
            {
                "source_status": "active",
                "index_eligible": True,
                "human_block": True,
            }
        )

        self.assertFalse(result["allowed"])
        self.assertEqual(result["reasons"], ["human_block"])

    def test_batch_counts_allowed_and_blocked_candidates(self) -> None:
        batch = build_entity_candidates(
            _load("extracted_text_entity_gate_mvp.json"),
            _load("file_records_entity_gate_mvp.json"),
            batch_ref="fixture://entity_gate",
        )

        self.assertEqual(batch["schema_version"], "capital.entity_extraction_candidate_batch.v1")
        self.assertEqual(batch["counts"]["input_extracted_text"], 3)
        self.assertEqual(batch["counts"]["allowed"], 1)
        self.assertEqual(batch["counts"]["blocked"], 2)
        self.assertEqual(batch["entity_extraction_candidates"][0]["next_action"], "extract_entities")
        self.assertEqual(batch["entity_extraction_candidates"][1]["next_action"], "blocked")
        self.assertEqual(batch["entity_extraction_candidates"][2]["next_action"], "blocked")


if __name__ == "__main__":
    unittest.main()
