from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from entity_extractor.extraction import (
    build_entity_extraction_prompt,
    build_entity_extraction_result,
)
from entity_extractor.source_guard import build_entity_candidates

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "entity-extractor"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class EntityExtractionTest(unittest.TestCase):
    def setUp(self) -> None:
        batch = build_entity_candidates(
            _load("extracted_text_entity_gate_mvp.json"),
            _load("file_records_entity_gate_mvp.json"),
            batch_ref="fixture://entity_gate",
        )
        self.extracted_items = _load("extracted_text_entity_gate_mvp.json")["extracted_text"]
        self.candidates = batch["entity_extraction_candidates"]

    def test_blocked_candidate_never_uses_ai_response(self) -> None:
        result = build_entity_extraction_result(
            self.candidates[1],
            self.extracted_items[1],
            _load("ai_response_entity_extraction_mvp.json"),
            provider_id="fixture",
            model_id="fixture-model",
        )

        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["gate_allowed"])
        self.assertEqual(result["entities"], [])
        self.assertEqual(result["relationships"], [])
        self.assertIn("source_status_not_active", result["issues"])

    def test_allowed_candidate_builds_normalized_entities_and_relationships(self) -> None:
        result = build_entity_extraction_result(
            self.candidates[0],
            self.extracted_items[0],
            _load("ai_response_entity_extraction_mvp.json"),
            provider_id="fixture",
            model_id="fixture-model",
        )

        self.assertEqual(result["status"], "extracted")
        self.assertTrue(result["gate_allowed"])
        self.assertEqual(len(result["entities"]), 2)
        self.assertEqual(len(result["relationships"]), 1)
        self.assertIn("dropped_entity_low_confidence", result["issues"])
        self.assertIn("dropped_relationship_low_confidence", result["issues"])
        self.assertRegex(result["entities"][0]["entity_id"], r"^entity_[a-f0-9]{24}$")
        self.assertRegex(result["relationships"][0]["relationship_id"], r"^relationship_[a-f0-9]{24}$")

    def test_empty_ai_response_goes_to_review(self) -> None:
        result = build_entity_extraction_result(
            self.candidates[0],
            self.extracted_items[0],
            {},
            provider_id="fixture",
            model_id="fixture-model",
        )

        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["entities"], [])
        self.assertIn("empty_ai_extraction", result["issues"])

    def test_prompt_is_refused_for_blocked_candidate(self) -> None:
        with self.assertRaises(ValueError):
            build_entity_extraction_prompt(self.candidates[1], self.extracted_items[1])

    def test_prompt_contains_output_schema_for_allowed_candidate(self) -> None:
        prompt = build_entity_extraction_prompt(self.candidates[0], self.extracted_items[0])

        self.assertIn("strict JSON", prompt["system"])
        payload = json.loads(prompt["user"])
        self.assertEqual(payload["file_id"], "file_active_001")
        self.assertIn("output_schema", payload)
        self.assertIn("text", payload)


if __name__ == "__main__":
    unittest.main()
