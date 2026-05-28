from __future__ import annotations

import unittest
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from entity_extractor.sheet_classifier import (
    build_sheet_classification_prompt,
    classify_sheet_row,
    normalize_sheet_classification,
)


class SheetClassifierTest(unittest.TestCase):
    def test_prompt_contains_file_context(self) -> None:
        prompt = build_sheet_classification_prompt(
            {
                "file_name": "Integra strategy.md",
                "parent_folder_name": "Integra Motors",
                "mime_type": "text/markdown",
                "content": "Sales funnel and CRM priorities.",
            }
        )

        self.assertIn("Integra strategy.md", prompt["user"])
        self.assertIn("Sales funnel", prompt["user"])
        self.assertIn("Return only JSON", prompt["system"])

    def test_normalize_clamps_score_and_action(self) -> None:
        result = normalize_sheet_classification(
            {
                "project": "Integra Motors Dubai",
                "summary_50w": "Important file",
                "value_score": 99,
                "action": "publish",
            }
        )

        self.assertEqual(result["value_score"], 5)
        self.assertEqual(result["action"], "REVIEW")

    def test_classify_sheet_row_uses_provider(self) -> None:
        calls: list[dict[str, str]] = []

        def provider(prompt: dict[str, str]) -> dict[str, object]:
            calls.append(prompt)
            return {
                "project": "Axon Agency",
                "sub_topic": "Automation",
                "type": "Technical note",
                "summary_50w": "Automation plan for Axon.",
                "linked_projects": "Axon Agency",
                "value_score": 4,
                "action": "KEEP",
            }

        result = classify_sheet_row({"file_name": "axon.md"}, provider=provider)

        self.assertEqual(len(calls), 1)
        self.assertEqual(result["project"], "Axon Agency")
        self.assertEqual(result["action"], "KEEP")


if __name__ == "__main__":
    unittest.main()
