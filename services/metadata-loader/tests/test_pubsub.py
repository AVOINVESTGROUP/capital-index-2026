from __future__ import annotations

import base64
import json
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from metadata_loader.drive_metadata import load_metadata_payload
from metadata_loader.pubsub import decode_pubsub_json, pubsub_message_ref


class PubSubEnvelopeTest(unittest.TestCase):
    def _normalized_payload(self) -> dict:
        fixture = (
            REPO_ROOT
            / "tests"
            / "fixtures"
            / "drive-events"
            / "normalized_probe_20260526T105738Z.json"
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
        decoded = decode_pubsub_json(self._envelope(self._normalized_payload()))

        self.assertEqual(decoded["schema_version"], "capital.event_batch.v1")
        self.assertEqual(len(decoded["events"]), 1)

    def test_pubsub_message_ref(self) -> None:
        self.assertEqual(pubsub_message_ref(self._envelope({}, message_id="abc")), "pubsub://message/abc")

    def test_pubsub_payload_loads_metadata(self) -> None:
        envelope = self._envelope(self._normalized_payload(), message_id="abc")
        result = load_metadata_payload(decode_pubsub_json(envelope), batch_ref=pubsub_message_ref(envelope))

        self.assertEqual(result["counts"]["file_upserts"], 1)
        self.assertEqual(result["file_upserts"][0]["raw_event_ref"], "pubsub://message/abc#/events/0")


if __name__ == "__main__":
    unittest.main()
