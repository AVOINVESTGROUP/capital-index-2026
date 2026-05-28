"""Controlled Pub/Sub publishing for downstream policy jobs."""

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
    return os.environ.get("PUBLISH_POLICY_JOBS", "false").lower() == "true"


def policy_topic_from_env() -> str:
    return os.environ.get("POLICY_JOBS_TOPIC", "capital.jobs.policy")


def publish_policy_job(
    batch: dict[str, Any],
    *,
    publisher: PublisherClient,
    project_id: str,
    topic_name: str,
    publish_enabled: bool,
) -> dict[str, Any]:
    upserts = batch.get("file_upserts") or []
    load_ids = [upsert.get("load_id") for upsert in upserts]
    if not publish_enabled:
        return {
            "status": "disabled",
            "topic": topic_name,
            "attempted": 0,
            "would_publish": 1 if upserts else 0,
            "load_ids": load_ids,
        }
    if not upserts:
        return {
            "status": "skipped",
            "topic": topic_name,
            "attempted": 0,
            "published": 0,
            "reason": "empty_batch",
            "load_ids": load_ids,
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
        "load_ids": load_ids,
    }


def pubsub_publisher() -> PublisherClient:
    from google.cloud import pubsub_v1

    return pubsub_v1.PublisherClient()
