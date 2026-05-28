from __future__ import annotations

import base64
import json
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from policy_engine.decision import apply_policy_payload
from policy_engine.pubsub import decode_pubsub_json, pubsub_message_ref


class PubSubEnvelopeTest(unittest.TestCase):
    def _metadata_payload(self) -> dict:
        fixture = (
            REPO_ROOT
            / "tests"
            / "fixtures"
            / "drive-events"
            / "file_metadata_probe_20260526T105738Z.json"
        )
        return json.loads(fixture.read_text(encoding="utf-8"))

    def _envelope(self, payload: dict, *, message_id: str = "msg-1") -> dict:
        raw = json.dumps(payload).encode("utf-8")
        return {
            "message": {
                "messageId": message_id,
                "data": base64.urlsafe_b64encode(raw).decode("ascii").rstrip("="),
            }
        }

    def test_decode_pubsub_json_without_padding(self) -> None:
        decoded = decode_pubsub_json(self._envelope(self._metadata_payload()))

        self.assertEqual(decoded["schema_version"], "capital.file_metadata_batch.v1")
        self.assertEqual(len(decoded["file_upserts"]), 1)

    def test_pubsub_message_ref(self) -> None:
        self.assertEqual(pubsub_message_ref(self._envelope({}, message_id="abc")), "pubsub://message/abc")

    def test_pubsub_payload_applies_policy(self) -> None:
        envelope = self._envelope(self._metadata_payload(), message_id="abc")
        result = apply_policy_payload(decode_pubsub_json(envelope), batch_ref=pubsub_message_ref(envelope))

        self.assertEqual(result["counts"]["policy_decisions"], 1)
        self.assertEqual(result["policy_decisions"][0]["raw_metadata_ref"], "pubsub://message/abc#/file_upserts/0")


if __name__ == "__main__":
    unittest.main()
