from __future__ import annotations

import base64
import json
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from event_ingestor.drive_changes import normalize_probe_payload
from event_ingestor.pubsub import decode_pubsub_json, pubsub_message_ref


class PubSubEnvelopeTest(unittest.TestCase):
    def _payload(self) -> dict:
        fixture = REPO_ROOT / "tests" / "fixtures" / "drive-events" / "probe_20260526T105738Z.json"
        return json.loads(fixture.read_text(encoding="utf-8"))

    def _envelope(self) -> dict:
        encoded = base64.b64encode(json.dumps(self._payload()).encode("utf-8")).decode("ascii")
        return {
            "message": {
                "data": encoded,
                "messageId": "test-message-001",
                "publishTime": "2026-05-27T00:00:00Z",
            },
            "subscription": "projects/capital-index-2026/subscriptions/capital.events.drive.ingestor.push",
        }

    def test_decode_pubsub_json(self) -> None:
        payload = decode_pubsub_json(self._envelope())

        self.assertEqual(payload["project_id"], "capital-index-2026")
        self.assertEqual(payload["counts"]["folder_changes"], 1)

    def test_decode_pubsub_json_without_padding(self) -> None:
        envelope = self._envelope()
        envelope["message"]["data"] = envelope["message"]["data"].rstrip("=")

        payload = decode_pubsub_json(envelope)

        self.assertEqual(payload["counts"]["folder_changes"], 1)

    def test_decode_pubsub_json_when_payload_is_json_string(self) -> None:
        payload_string = json.dumps(json.dumps(self._payload()))
        envelope = {
            "message": {
                "data": base64.b64encode(payload_string.encode("utf-8")).decode("ascii"),
                "messageId": "test-message-string",
            }
        }

        payload = decode_pubsub_json(envelope)

        self.assertEqual(payload["counts"]["folder_changes"], 1)

    def test_pubsub_message_ref(self) -> None:
        self.assertEqual(pubsub_message_ref(self._envelope()), "pubsub://message/test-message-001")

    def test_pubsub_payload_normalizes(self) -> None:
        envelope = self._envelope()
        payload = decode_pubsub_json(envelope)
        result = normalize_probe_payload(payload, fixture_ref=pubsub_message_ref(envelope))

        self.assertEqual(result["fixture_path"], "pubsub://message/test-message-001")
        self.assertEqual(result["events"][0]["raw_payload_ref"], "pubsub://message/test-message-001#/folder_changes/0")

    def test_missing_message_rejected(self) -> None:
        with self.assertRaises(ValueError):
            decode_pubsub_json({})


if __name__ == "__main__":
    unittest.main()
