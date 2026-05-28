from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from content_extractor.docs_reader import extract_text, make_extraction_result

DOCS_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "docs"
DRIVE_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "drive-events"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _doc() -> dict:
    return _load(DOCS_FIXTURES / "doc_response_20260526T105738Z.json")


def _plan() -> dict:
    batch = _load(DRIVE_FIXTURES / "normalized_probe_20260526T105738Z.json")
    event = batch["events"][0]
    policy = _load(DRIVE_FIXTURES / "policy_decision_20260526T105738Z.json")

    sys.path.insert(0, str(REPO_ROOT / "services" / "event-ingestor" / "src"))
    from event_ingestor.extraction_plan import make_extraction_plan
    return make_extraction_plan(event, policy)


class DocsReaderTest(unittest.TestCase):
    def test_extract_text_returns_all_runs(self) -> None:
        text = extract_text(_doc())

        self.assertIn("CAPITAL INDEX probe test doc.", text)
        self.assertIn("This file was created to test Drive ingestion.", text)

    def test_extract_text_empty_doc(self) -> None:
        text = extract_text({"body": {"content": []}})
        self.assertEqual(text, "")

    def test_extract_text_doc_without_body(self) -> None:
        text = extract_text({})
        self.assertEqual(text, "")

    def test_table_text_is_included(self) -> None:
        doc = {
            "body": {
                "content": [
                    {
                        "table": {
                            "tableRows": [
                                {
                                    "tableCells": [
                                        {
                                            "content": [
                                                {
                                                    "paragraph": {
                                                        "elements": [
                                                            {"textRun": {"content": "cell text\n"}}
                                                        ]
                                                    }
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ]
            }
        }
        self.assertIn("cell text", extract_text(doc))

    def test_make_extraction_result_structure(self) -> None:
        result = make_extraction_result(_plan(), _doc())

        self.assertEqual(result["schema_version"], "capital.extracted_text.v1")
        self.assertEqual(result["file_id"], "1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM")
        self.assertEqual(result["doc_title"], "drive-probe-test-001")
        self.assertGreater(result["char_count"], 0)
        self.assertEqual(result["char_count"], len(result["text"]))
        self.assertEqual(result["next_action"], "classify")
        self.assertFalse(result["embedding_allowed"])
        self.assertFalse(result["vault_publish_allowed"])
        self.assertFalse(result["ai_context_allowed"])

    def test_empty_doc_goes_to_review(self) -> None:
        empty_doc = {"documentId": "x", "title": "empty", "body": {"content": []}}
        result = make_extraction_result(_plan(), empty_doc)

        self.assertEqual(result["next_action"], "review_required")
        self.assertEqual(result["char_count"], 0)

    def test_live_probe_empty_doc_goes_to_review(self) -> None:
        doc = _load(DOCS_FIXTURES / "doc_response_probe_20260526T105738Z.json")
        result = make_extraction_result(_plan(), doc)

        self.assertEqual(result["doc_title"], "drive-probe-test-001")
        self.assertEqual(result["text"].strip(), "")
        self.assertEqual(result["next_action"], "review_required")


if __name__ == "__main__":
    unittest.main()
