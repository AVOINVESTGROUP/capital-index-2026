from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from entity_extractor.worker import build_entity_extraction_batch

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "entity-extractor"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class WorkerTest(unittest.TestCase):
    def test_build_entity_extraction_batch_counts_statuses(self) -> None:
        batch = build_entity_extraction_batch(
            _load("extracted_text_entity_gate_mvp.json"),
            _load("file_records_entity_gate_mvp.json"),
            batch_ref="fixture://entity_gate",
            ai_responses_by_file_id={"file_active_001": _load("ai_response_entity_extraction_mvp.json")},
            provider_id="fixture",
            model_id="fixture-model",
        )

        self.assertEqual(batch["schema_version"], "capital.entity_extraction_batch.v1")
        self.assertEqual(batch["counts"]["input_extracted_text"], 3)
        self.assertEqual(batch["counts"]["extracted"], 1)
        self.assertEqual(batch["counts"]["blocked"], 2)
        self.assertEqual(batch["counts"]["needs_review"], 0)
        self.assertEqual(len(batch["entity_extractions"]), 3)

    def test_allowed_without_ai_response_goes_to_review(self) -> None:
        batch = build_entity_extraction_batch(
            _load("extracted_text_entity_gate_mvp.json"),
            _load("file_records_entity_gate_mvp.json"),
            batch_ref="fixture://entity_gate",
        )

        self.assertEqual(batch["counts"]["needs_review"], 1)
        self.assertEqual(batch["entity_extractions"][0]["status"], "needs_review")

    def test_provider_is_called_only_for_allowed_candidates(self) -> None:
        calls: list[str] = []

        def provider(candidate: dict, extracted_text: dict) -> dict:
            calls.append(candidate["file_id"])
            return _load("ai_response_entity_extraction_mvp.json")

        batch = build_entity_extraction_batch(
            _load("extracted_text_entity_gate_mvp.json"),
            _load("file_records_entity_gate_mvp.json"),
            batch_ref="fixture://entity_gate",
            ai_response_provider=provider,
            provider_id="fixture",
            model_id="fixture-model",
        )

        self.assertEqual(calls, ["file_active_001"])
        self.assertEqual(batch["counts"]["extracted"], 1)


if __name__ == "__main__":
    unittest.main()
