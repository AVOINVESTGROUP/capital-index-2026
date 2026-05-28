from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from entity_extractor.ai_provider import (
    DisabledAIProvider,
    ai_provider_enabled_from_env,
    ai_response_schema,
    parse_gemini_response,
    parse_openai_response,
    provider_from_env,
)


class AIProviderTest(unittest.TestCase):
    def test_parse_openai_response_accepts_output_text(self) -> None:
        result = parse_openai_response(
            {
                "output_text": json.dumps(
                    {
                        "entities": [],
                        "relationships": [],
                    }
                )
            }
        )

        self.assertEqual(result["entities"], [])
        self.assertEqual(result["relationships"], [])

    def test_parse_openai_response_accepts_output_content_text(self) -> None:
        result = parse_openai_response(
            {
                "output": [
                    {
                        "content": [
                            {
                                "type": "output_text",
                                "text": "{\"entities\": [], \"relationships\": []}",
                            }
                        ]
                    }
                ]
            }
        )

        self.assertEqual(result["entities"], [])

    def test_parse_gemini_response_accepts_candidate_part_text(self) -> None:
        result = parse_gemini_response(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": "{\"entities\": [], \"relationships\": []}",
                                }
                            ]
                        }
                    }
                ]
            }
        )

        self.assertEqual(result["relationships"], [])

    def test_schema_requires_entities_and_relationships(self) -> None:
        schema = ai_response_schema()

        self.assertEqual(schema["required"], ["entities", "relationships"])
        self.assertFalse(schema["additionalProperties"])

    def test_provider_is_disabled_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(ai_provider_enabled_from_env())
            self.assertIsInstance(provider_from_env(), DisabledAIProvider)

    def test_openai_provider_requires_secret_when_enabled(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER_ENABLED": "true",
                "AI_PROVIDER": "openai",
                "OPENAI_MODEL_ID": "gpt-fixture",
            },
            clear=True,
        ):
            with self.assertRaises(ValueError):
                provider_from_env()


if __name__ == "__main__":
    unittest.main()
