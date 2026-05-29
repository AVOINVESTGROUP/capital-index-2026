import sys
import unittest
from pathlib import Path

SERVICE_SRC = Path(__file__).resolve().parents[1] / "src"
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SERVICE_SRC))
sys.path.insert(0, str(TESTS_DIR))

from context_publisher.ai_reading import build_bundle_reading, build_bundle_reading_prompt
from test_builder import sample_source
from context_publisher.builder import build_second_brain_publication


class FakeReadingProvider:
    provider_id = "fake_ai"
    model_id = "fake-model"

    def generate(self, *, system, user):
        self.system = system
        self.user = user
        return {
            "executive_summary": "AI learned that Capital Index maps projects and links files to decisions.",
            "what_ai_learned": [
                {"point": "Capital Index maps projects.", "source_evidence_ids": ["evidence_1"]}
            ],
            "key_themes": [
                {
                    "theme": "Project intelligence",
                    "why_it_matters": "It connects documents to decisions.",
                    "source_evidence_ids": ["evidence_1"],
                }
            ],
            "risks": [],
            "open_questions": [{"question": "Which files are still missing?", "source_evidence_ids": []}],
            "recommended_next_actions": [
                {"action": "Review blocked sources.", "reason": "Coverage is incomplete.", "source_evidence_ids": []}
            ],
            "source_evidence_ids": ["evidence_1"],
            "confidence": 0.8,
        }


class AIReadingTest(unittest.TestCase):
    def test_prompt_contains_evidence_and_claims(self):
        publication = build_second_brain_publication(sample_source())
        system, user = build_bundle_reading_prompt(publication)

        self.assertIn("source_evidence_ids", system)
        self.assertIn("Capital Index", user)
        self.assertIn("evidence_", user)

    def test_build_bundle_reading_normalizes_ai_output(self):
        publication = build_second_brain_publication(sample_source())
        reading = build_bundle_reading(publication, provider=FakeReadingProvider())

        self.assertEqual(reading["status"], "generated")
        self.assertEqual(reading["provider_id"], "fake_ai")
        self.assertEqual(reading["model_id"], "fake-model")
        self.assertEqual(reading["confidence"], 0.8)
        self.assertEqual(reading["what_ai_learned"][0]["point"], "Capital Index maps projects.")


if __name__ == "__main__":
    unittest.main()
