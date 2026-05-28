from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from entity_extractor.extraction import build_entity_extraction_result
from entity_extractor.source_guard import build_entity_candidates

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "entity-extractor"

CANDIDATE_ID = re.compile(r"^entity_candidate_[a-f0-9]{24}$")
EXTRACTION_ID = re.compile(r"^entity_extraction_[a-f0-9]{24}$")
ENTITY_ID = re.compile(r"^entity_[a-f0-9]{24}$")
RELATIONSHIP_ID = re.compile(r"^relationship_[a-f0-9]{24}$")
SOURCE_STATUSES = {
    "active",
    "candidate_duplicate",
    "candidate_stale",
    "candidate_empty",
    "candidate_archive",
    "do_not_index",
    "needs_human_review",
    None,
}
GATE_REASONS = {
    "source_status_not_active",
    "index_eligible_not_true",
    "human_block",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class SchemaContractsTest(unittest.TestCase):
    def test_entity_candidates_match_contract(self) -> None:
        batch = build_entity_candidates(
            _load(FIXTURES / "extracted_text_entity_gate_mvp.json"),
            _load(FIXTURES / "file_records_entity_gate_mvp.json"),
            batch_ref="fixture://entity_gate",
        )

        for item in batch["entity_extraction_candidates"]:
            self.assertEqual(item["schema_version"], "capital.entity_extraction_candidate.v1")
            self.assertRegex(item["candidate_id"], CANDIDATE_ID)
            self.assertTrue(item["file_id"])
            self.assertGreaterEqual(item["char_count"], 0)
            self.assertIn(item["source_status"], SOURCE_STATUSES)
            self.assertIn(item["index_eligible"], {True, False, None})
            self.assertIsInstance(item["human_block"], bool)
            self.assertIsInstance(item["gate_allowed"], bool)
            self.assertIn(item["gate_reason"], {"allowed", "blocked_by_drive_governance"})
            self.assertTrue(set(item["gate_reasons"]).issubset(GATE_REASONS))
            self.assertIn(item["next_action"], {"extract_entities", "blocked"})

            if item["gate_allowed"]:
                self.assertEqual(item["source_status"], "active")
                self.assertTrue(item["index_eligible"])
                self.assertEqual(item["gate_reasons"], [])
            else:
                self.assertNotEqual(item["next_action"], "extract_entities")

    def test_extracted_entities_match_contract(self) -> None:
        extracted_batch = _load(FIXTURES / "extracted_text_entity_gate_mvp.json")
        candidates = build_entity_candidates(
            extracted_batch,
            _load(FIXTURES / "file_records_entity_gate_mvp.json"),
            batch_ref="fixture://entity_gate",
        )["entity_extraction_candidates"]

        result = build_entity_extraction_result(
            candidates[0],
            extracted_batch["extracted_text"][0],
            _load(FIXTURES / "ai_response_entity_extraction_mvp.json"),
            provider_id="fixture",
            model_id="fixture-model",
        )

        self.assertEqual(result["schema_version"], "capital.extracted_entities.v1")
        self.assertRegex(result["extraction_id"], EXTRACTION_ID)
        self.assertRegex(result["candidate_id"], CANDIDATE_ID)
        self.assertEqual(result["status"], "extracted")
        self.assertTrue(result["gate_allowed"])
        self.assertGreaterEqual(result["input_char_count"], 0)
        self.assertIsInstance(result["issues"], list)

        for entity in result["entities"]:
            self.assertRegex(entity["entity_id"], ENTITY_ID)
            self.assertTrue(entity["name"])
            self.assertGreaterEqual(entity["confidence"], 0)
            self.assertLessEqual(entity["confidence"], 1)
            self.assertIsInstance(entity["attributes"], dict)

        for relationship in result["relationships"]:
            self.assertRegex(relationship["relationship_id"], RELATIONSHIP_ID)
            self.assertTrue(relationship["relationship_type"])
            self.assertTrue(relationship["from_id"])
            self.assertTrue(relationship["to_id"])
            self.assertGreaterEqual(relationship["confidence"], 0.75)
            self.assertIsInstance(relationship["evidence_file_ids"], list)
            self.assertIsInstance(relationship["evidence_artifact_ids"], list)


if __name__ == "__main__":
    unittest.main()
