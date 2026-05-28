from __future__ import annotations

import base64
import json
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from content_extractor.extraction import extract_from_policy_payload
from content_extractor.pubsub import decode_pubsub_json, pubsub_message_ref
from test_extraction import FakeDocsService


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class PubSubEnvelopeTest(unittest.TestCase):
    def _policy_payload(self) -> dict:
        return _load(REPO_ROOT / "tests" / "fixtures" / "drive-events" / "policy_decision_probe_20260526T105738Z.json")

    def _envelope(self, payload: dict, *, message_id: str = "msg-1") -> dict:
        raw = json.dumps(payload).encode("utf-8")
        return {
            "message": {
                "messageId": message_id,
                "data": base64.urlsafe_b64encode(raw).decode("ascii").rstrip("="),
            }
        }

    def test_decode_pubsub_json_without_padding(self) -> None:
        decoded = decode_pubsub_json(self._envelope(self._policy_payload()))

        self.assertEqual(decoded["schema_version"], "capital.policy_decision_batch.v1")
        self.assertEqual(len(decoded["policy_decisions"]), 1)

    def test_pubsub_payload_extracts(self) -> None:
        doc = _load(REPO_ROOT / "tests" / "fixtures" / "docs" / "doc_response_20260526T105738Z.json")
        envelope = self._envelope(self._policy_payload(), message_id="abc")
        result = extract_from_policy_payload(
            decode_pubsub_json(envelope),
            batch_ref=pubsub_message_ref(envelope),
            docs_service=FakeDocsService(doc),
            docs_read_enabled=True,
        )

        self.assertEqual(result["extracted_text"][0]["raw_policy_ref"], "pubsub://message/abc#/policy_decisions/0")


if __name__ == "__main__":
    unittest.main()
