"""Controlled Pub/Sub publishing for downstream extraction jobs."""

from __future__ import annotations

import json
import os
from typing import Any, Protocol


class PublishFuture(Protocol):
    def result(self, timeout: float | None = None) -> str:
        ...


class PublisherClient(Protocol):
    def topic_path(self, project_id: str, topic_name: str) -> str:
        ...

    def publish(self, topic_path: str, data: bytes, **attrs: str) -> PublishFuture:
        ...


def publish_enabled_from_env() -> bool:
    return os.environ.get("PUBLISH_EXTRACTION_JOBS", "false").lower() == "true"


def extraction_topic_from_env() -> str:
    return os.environ.get("EXTRACTION_JOBS_TOPIC", "capital.jobs.extraction")


def publish_extraction_job(
    batch: dict[str, Any],
    *,
    publisher: PublisherClient,
    project_id: str,
    topic_name: str,
    publish_enabled: bool,
) -> dict[str, Any]:
    decisions = batch.get("policy_decisions") or []
    decision_ids = [decision.get("decision_id") for decision in decisions]
    candidates = [
        decision
        for decision in decisions
        if not decision.get("review_required")
        and decision.get("next_action") == "content_extraction_candidate"
        and "read_content" in (decision.get("allowed_actions") or [])
    ]

    if not publish_enabled:
        return {
            "status": "disabled",
            "topic": topic_name,
            "attempted": 0,
            "would_publish": 1 if candidates else 0,
            "decision_ids": decision_ids,
        }
    if not candidates:
        return {
            "status": "skipped",
            "topic": topic_name,
            "attempted": 0,
            "published": 0,
            "reason": "no_extraction_candidates",
            "decision_ids": decision_ids,
        }

    topic_path = publisher.topic_path(project_id, topic_name)
    data = json.dumps(batch, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    future = publisher.publish(
        topic_path,
        data,
        schema_version=str(batch.get("schema_version") or ""),
        source=str(batch.get("source") or ""),
    )
    message_id = future.result(timeout=30)
    return {
        "status": "published",
        "topic": topic_name,
        "attempted": 1,
        "published": 1,
        "message_id": message_id,
        "decision_ids": decision_ids,
    }


def pubsub_publisher() -> PublisherClient:
    from google.cloud import pubsub_v1

    return pubsub_v1.PublisherClient()
