"""Helpers for Pub/Sub push envelopes."""

from __future__ import annotations

import base64
import json
from typing import Any


def decode_pubsub_json(envelope: dict[str, Any]) -> dict[str, Any]:
    message = envelope.get("message")
    if not isinstance(message, dict):
        raise ValueError("Pub/Sub envelope missing message object")
    encoded = message.get("data")
    if not encoded:
        raise ValueError("Pub/Sub message missing data")
    try:
        padded = encoded + "=" * (-len(encoded) % 4)
        raw = base64.urlsafe_b64decode(padded).decode("utf-8")
        decoded = json.loads(raw)
        if isinstance(decoded, str):
            decoded = json.loads(decoded)
        if not isinstance(decoded, dict):
            raise ValueError("Decoded Pub/Sub payload is not a JSON object")
        return decoded
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid Pub/Sub JSON payload: {exc}") from exc


def pubsub_message_ref(envelope: dict[str, Any]) -> str:
    message = envelope.get("message") or {}
    message_id = message.get("messageId") or message.get("message_id") or "unknown"
    return f"pubsub://message/{message_id}"
