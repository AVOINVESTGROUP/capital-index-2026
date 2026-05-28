from __future__ import annotations

import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from drive_governance.source_classifier import classify_batch, classify_source_file


class SourceClassifierTest(unittest.TestCase):
    def test_readable_docs_become_active(self) -> None:
        result = classify_source_file(
            {
                "file_id": "doc1",
                "name": "AI_TODAY_CONTEXT",
                "mime_type": "application/vnd.google-apps.document",
                "source_status": "needs_human_review",
            }
        )

        self.assertEqual(result["new_source_status"], "active")
        self.assertTrue(result["new_index_eligible"])
        self.assertEqual(result["rule_id"], "readable_business_source")

    def test_technical_files_are_blocked(self) -> None:
        result = classify_source_file(
            {
                "file_id": "script1",
                "name": "transh_people_structure.ps1",
                "mime_type": "application/octet-stream",
                "source_status": "needs_human_review",
            }
        )

        self.assertEqual(result["new_source_status"], "do_not_index")
        self.assertFalse(result["new_index_eligible"])
        self.assertTrue(result["new_human_block"])

    def test_human_decision_is_preserved(self) -> None:
        result = classify_source_file(
            {
                "file_id": "approved1",
                "name": "2026-05-27.md",
                "mime_type": "text/markdown",
                "source_status": "active",
                "index_eligible": True,
                "source_approved_by": "office@example.com",
            }
        )

        self.assertEqual(result["new_source_status"], "active")
        self.assertTrue(result["new_index_eligible"])
        self.assertEqual(result["rule_id"], "preserve_human_decision")

    def test_archive_names_become_cleanup_candidates(self) -> None:
        result = classify_source_file(
            {
                "file_id": "old1",
                "name": "Project backup old.md",
                "mime_type": "text/markdown",
                "source_status": "needs_human_review",
            }
        )

        self.assertEqual(result["new_source_status"], "candidate_archive")
        self.assertFalse(result["new_index_eligible"])

    def test_batch_counts_decisions(self) -> None:
        result = classify_batch(
            [
                {"file_id": "a", "name": "Doc", "mime_type": "application/vnd.google-apps.document"},
                {"file_id": "b", "name": "run.ps1", "mime_type": "application/octet-stream"},
            ]
        )

        self.assertEqual(result["counts"]["input_files"], 2)
        self.assertEqual(result["counts"]["active"], 1)
        self.assertEqual(result["counts"]["do_not_index"], 1)

    def test_older_dated_context_is_stale_in_batch(self) -> None:
        result = classify_batch(
            [
                {
                    "file_id": "old",
                    "name": "AI_TODAY_CONTEXT_2026-05-22_2026-05-22_14-10-22",
                    "mime_type": "application/vnd.google-apps.document",
                },
                {
                    "file_id": "new",
                    "name": "AI_TODAY_CONTEXT_2026-05-27_2026-05-27_12-40-24",
                    "mime_type": "application/vnd.google-apps.document",
                },
            ]
        )

        decisions = {item["file_id"]: item for item in result["decisions"]}
        self.assertEqual(decisions["old"]["new_source_status"], "candidate_stale")
        self.assertFalse(decisions["old"]["new_index_eligible"])
        self.assertEqual(decisions["new"]["new_source_status"], "active")

    def test_prompt_templates_are_not_project_context(self) -> None:
        result = classify_source_file(
            {
                "file_id": "prompt",
                "name": "Fix grammar and spelling.md",
                "mime_type": "text/markdown",
            }
        )

        self.assertEqual(result["new_source_status"], "do_not_index")
        self.assertEqual(result["rule_id"], "prompt_template_not_project_context")


if __name__ == "__main__":
    unittest.main()
