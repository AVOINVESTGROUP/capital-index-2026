import sys
import unittest
from pathlib import Path

SERVICE_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SERVICE_SRC))

from context_publisher.builder import build_second_brain_publication


def sample_source():
    return {
        "owner_profile": {"name": "Owner", "role": "final approval authority"},
        "policy_snapshot_id": "policy_001",
        "files": [
            {
                "file_id": "file_active",
                "name": "Active Doc",
                "source_status": "active",
                "index_eligible": True,
                "human_block": False,
                "web_view_link": "https://drive.example/file_active",
                "project_id": "capital_index",
            },
            {
                "file_id": "file_blocked",
                "name": "Blocked Doc",
                "source_status": "needs_human_review",
                "index_eligible": False,
                "human_block": False,
            },
        ],
        "extracted_text": [
            {
                "file_id": "file_active",
                "plan_id": "plan_1",
                "doc_title": "Active Doc",
                "text": "Capital Index maps projects. It links files to decisions.",
                "char_count": 57,
                "ai_context_allowed": True,
            },
            {
                "file_id": "file_blocked",
                "plan_id": "plan_blocked",
                "text": "This must not enter the bundle.",
                "ai_context_allowed": True,
            },
        ],
        "entity_extractions": [
            {
                "file_id": "file_active",
                "status": "extracted",
                "entities": [
                    {
                        "entity_id": "entity_capital_index",
                        "type": "PROJECT",
                        "name": "Capital Index",
                        "confidence": 0.91,
                        "evidence_text": "Capital Index",
                        "attributes": {"domain": "second_brain"},
                    }
                ],
                "relationships": [
                    {
                        "relationship_id": "rel_maps_projects",
                        "relationship_type": "maps",
                        "from_id": "Capital Index",
                        "to_id": "projects",
                        "confidence": 0.8,
                        "evidence_file_ids": ["file_active"],
                        "evidence_artifact_ids": ["plan_1"],
                        "reason": "The text says it maps projects.",
                    }
                ],
            }
        ],
        "review_queue": [],
        "cleanup_queue": [],
    }


class ContextBuilderTest(unittest.TestCase):
    def test_builds_evidence_first_publication(self):
        publication = build_second_brain_publication(sample_source())

        self.assertEqual(publication["schema_version"], "capital.context_publication.v1")
        self.assertEqual(publication["counts"]["source_files"], 1)
        self.assertEqual(publication["counts"]["extracted_text"], 1)
        self.assertEqual(publication["counts"]["evidence"], 1)
        self.assertEqual(publication["counts"]["entities"], 1)
        self.assertEqual(publication["counts"]["relationships"], 1)
        self.assertGreaterEqual(publication["counts"]["claims"], 3)

        bundle = publication["bundle"]
        self.assertEqual(bundle["approval_status"], "draft")
        self.assertTrue(bundle["requires_human_approval"])
        self.assertEqual(bundle["source_file_ids"], ["file_active"])
        self.assertEqual(bundle["included_extracted_text_file_ids"], ["file_active"])
        self.assertEqual(bundle["policy_snapshot_id"], "policy_001")
        self.assertNotIn("file_blocked", bundle["body"]["source_file_ids"])
        self.assertEqual(bundle["omitted_or_blocked_sources"][0]["file_id"], "file_blocked")

    def test_vault_projection_is_preview_with_protected_block(self):
        publication = build_second_brain_publication(sample_source())
        projection = publication["vault_projection"]

        self.assertEqual(projection["schema_version"], "capital.vault_projection.v1")
        self.assertEqual(projection["write_status"], "preview")
        self.assertTrue(projection["requires_approval"])
        self.assertIn("CAPITAL_INDEX:GENERATED_START", projection["content"])
        self.assertIn("Manual Notes", projection["content"])

    def test_entities_are_not_published_without_evidence(self):
        source = sample_source()
        source["extracted_text"][0]["ai_context_allowed"] = False

        publication = build_second_brain_publication(source)

        self.assertEqual(publication["counts"]["evidence"], 0)
        self.assertEqual(publication["counts"]["entities"], 0)
        self.assertEqual(publication["counts"]["relationships"], 0)
        self.assertEqual(publication["counts"]["claims"], 0)
        self.assertEqual(publication["bundle"]["body"]["recent_claims"], [])


if __name__ == "__main__":
    unittest.main()
