from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from policy_engine.decision import apply_policy_batch
from policy_engine.job_publisher import publish_extraction_job


class FakeFuture:
    def result(self, timeout: float | None = None) -> str:
        return "msg-extract-123"


class FakePublisher:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def topic_path(self, project_id: str, topic_name: str) -> str:
        return f"projects/{project_id}/topics/{topic_name}"

    def publish(self, topic_path: str, data: bytes, **attrs: str) -> FakeFuture:
        self.calls.append({"topic_path": topic_path, "data": data, "attrs": attrs})
        return FakeFuture()


class JobPublisherTest(unittest.TestCase):
    def _batch(self) -> dict:
        fixture = (
            REPO_ROOT
            / "tests"
            / "fixtures"
            / "drive-events"
            / "file_metadata_probe_20260526T105738Z.json"
        )
        return apply_policy_batch(fixture)

    def test_publish_disabled_does_not_call_pubsub(self) -> None:
        publisher = FakePublisher()
        result = publish_extraction_job(
            self._batch(),
            publisher=publisher,
            project_id="capital-index-2026",
            topic_name="capital.jobs.extraction",
            publish_enabled=False,
        )

        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["would_publish"], 1)
        self.assertEqual(publisher.calls, [])

    def test_publish_enabled_sends_candidate_batch(self) -> None:
        publisher = FakePublisher()
        result = publish_extraction_job(
            self._batch(),
            publisher=publisher,
            project_id="capital-index-2026",
            topic_name="capital.jobs.extraction",
            publish_enabled=True,
        )

        self.assertEqual(result["status"], "published")
        self.assertEqual(result["message_id"], "msg-extract-123")
        self.assertEqual(len(publisher.calls), 1)
        call = publisher.calls[0]
        self.assertEqual(call["topic_path"], "projects/capital-index-2026/topics/capital.jobs.extraction")
        payload = json.loads(call["data"].decode("utf-8"))
        self.assertEqual(payload["schema_version"], "capital.policy_decision_batch.v1")
        self.assertEqual(call["attrs"]["source"], "policy_engine_worker")

    def test_no_candidate_skips_publish(self) -> None:
        batch = self._batch()
        batch["policy_decisions"][0]["review_required"] = True
        publisher = FakePublisher()

        result = publish_extraction_job(
            batch,
            publisher=publisher,
            project_id="capital-index-2026",
            topic_name="capital.jobs.extraction",
            publish_enabled=True,
        )

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "no_extraction_candidates")
        self.assertEqual(publisher.calls, [])


if __name__ == "__main__":
    unittest.main()
