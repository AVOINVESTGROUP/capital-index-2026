from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from event_ingestor.extraction_plan import make_extraction_plan

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "drive-events"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _event() -> dict:
    batch = _load("normalized_probe_20260526T105738Z.json")
    return batch["events"][0]


def _policy() -> dict:
    return _load("policy_decision_20260526T105738Z.json")


class ExtractionPlanTest(unittest.TestCase):
    def test_allowed_doc_gets_extract_text(self) -> None:
        plan = make_extraction_plan(_event(), _policy())

        self.assertEqual(plan["next_action"], "extract_text")
        self.assertTrue(plan["can_read_content"])
        self.assertTrue(plan["can_extract_text"])
        self.assertTrue(plan["text_only"])
        self.assertFalse(plan["embedding_allowed"])
        self.assertFalse(plan["vault_publish_allowed"])
        self.assertFalse(plan["ai_context_allowed"])
        self.assertEqual(plan["sensitivity_class"], "BUSINESS_CONFIDENTIAL")
        self.assertTrue(plan["plan_id"].startswith("plan_"))
        self.assertEqual(len(plan["plan_id"]), 29)  # "plan_" + 24 hex chars

    def test_denied_policy_blocks_read(self) -> None:
        policy = {"decision": "deny", "sensitivity_class": "SECRET", "allowed_actions": []}
        plan = make_extraction_plan(_event(), policy)

        self.assertEqual(plan["next_action"], "blocked")
        self.assertFalse(plan["can_read_content"])
        self.assertFalse(plan["can_extract_text"])

    def test_plan_id_is_deterministic(self) -> None:
        plan1 = make_extraction_plan(_event(), _policy())
        plan2 = make_extraction_plan(_event(), _policy())

        self.assertEqual(plan1["plan_id"], plan2["plan_id"])

    def test_unknown_mime_type_goes_to_review(self) -> None:
        event = _event().copy()
        event["file"] = dict(event["file"], mime_type="application/octet-stream")
        plan = make_extraction_plan(event, _policy())

        self.assertEqual(plan["next_action"], "review_required")
        self.assertFalse(plan["can_extract_text"])


if __name__ == "__main__":
    unittest.main()
