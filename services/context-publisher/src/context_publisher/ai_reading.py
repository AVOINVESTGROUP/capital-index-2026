"""AI-generated human reading layer for context bundles."""

from __future__ import annotations

import json
import os
from typing import Any, Protocol

import requests

from context_publisher.secret_manager import gemini_api_key_from_env


class BundleReadingProvider(Protocol):
    provider_id: str
    model_id: str

    def generate(self, *, system: str, user: str) -> dict[str, Any]:
        ...


class DisabledBundleReadingProvider:
    provider_id = "disabled"
    model_id = "not_called"

    def generate(self, *, system: str, user: str) -> dict[str, Any]:
        raise RuntimeError("AI bundle reading is disabled")


class GeminiBundleReadingProvider:
    provider_id = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model_id: str,
        endpoint_base: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_seconds: int = 90,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key is required")
        if not model_id:
            raise ValueError("Gemini model id is required")
        self.api_key = api_key
        self.model_id = model_id
        self.endpoint_base = endpoint_base.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def generate(self, *, system: str, user: str) -> dict[str, Any]:
        response = requests.post(
            f"{self.endpoint_base}/models/{self.model_id}:generateContent",
            headers={
                "content-type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            json={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.1,
                },
            },
            timeout=self.timeout_seconds,
        )
        if not response.ok:
            raise RuntimeError(f"Gemini bundle reading failed: {response.status_code} {response.text}")
        return parse_gemini_response(response.json())


def ai_reading_enabled_from_env() -> bool:
    return os.environ.get("AI_READING_ENABLED", "false").lower() == "true"


def provider_from_env() -> BundleReadingProvider:
    if not ai_reading_enabled_from_env():
        return DisabledBundleReadingProvider()

    provider = os.environ.get("AI_READING_PROVIDER", "gemini").lower()
    if provider != "gemini":
        raise ValueError(f"Unsupported AI_READING_PROVIDER: {provider}")

    return GeminiBundleReadingProvider(
        api_key=gemini_api_key_from_env(),
        model_id=os.environ.get("GEMINI_MODEL_ID", "gemini-2.5-flash").strip(),
        endpoint_base=os.environ.get("GEMINI_ENDPOINT_BASE", "https://generativelanguage.googleapis.com/v1beta"),
        timeout_seconds=_timeout_from_env(),
    )


def build_bundle_reading(
    publication: dict[str, Any],
    *,
    provider: BundleReadingProvider | None = None,
) -> dict[str, Any]:
    provider = provider or provider_from_env()
    system, user = build_bundle_reading_prompt(publication)
    result = provider.generate(system=system, user=user)
    normalized = normalize_bundle_reading(result)
    normalized.update(
        {
            "schema_version": "capital.ai_bundle_reading.v1",
            "status": "generated",
            "provider_id": provider.provider_id,
            "model_id": provider.model_id,
            "created_by_agent": "context-publisher-agent",
        }
    )
    return normalized


def disabled_bundle_reading(reason: str = "ai_reading_disabled") -> dict[str, Any]:
    return {
        "schema_version": "capital.ai_bundle_reading.v1",
        "status": "not_generated",
        "reason": reason,
        "provider_id": "disabled",
        "model_id": "not_called",
        "executive_summary": "",
        "what_ai_learned": [],
        "key_themes": [],
        "risks": [],
        "open_questions": [],
        "recommended_next_actions": [],
        "source_evidence_ids": [],
        "confidence": 0,
        "created_by_agent": "context-publisher-agent",
    }


def failed_bundle_reading(error: Exception) -> dict[str, Any]:
    reading = disabled_bundle_reading("ai_reading_failed")
    reading["status"] = "failed"
    reading["error"] = str(error)[:1000]
    return reading


def build_bundle_reading_prompt(publication: dict[str, Any]) -> tuple[str, str]:
    bundle = publication.get("bundle") or {}
    evidence = publication.get("source_evidence") or []
    claims = publication.get("claims") or []
    relationships = publication.get("relationships") or []

    compact_input = {
        "bundle_id": bundle.get("bundle_id"),
        "bundle_type": bundle.get("bundle_type"),
        "counts": publication.get("counts") or {},
        "evidence": [
            {
                "evidence_id": item.get("evidence_id"),
                "file_id": item.get("file_id"),
                "title": item.get("title"),
                "project_id": item.get("project_id"),
                "snippet": item.get("snippet"),
            }
            for item in evidence[:60]
        ],
        "claims": [
            {
                "claim_id": item.get("claim_id"),
                "claim_type": item.get("claim_type"),
                "text": item.get("text"),
                "confidence": item.get("confidence"),
                "evidence_ids": item.get("evidence_ids") or [],
            }
            for item in claims[:120]
        ],
        "relationships": [
            {
                "relationship_id": item.get("relationship_id"),
                "relationship_type": item.get("relationship_type"),
                "from_id": item.get("from_id"),
                "to_id": item.get("to_id"),
                "confidence": item.get("confidence"),
                "evidence_ids": item.get("evidence_ids") or [],
                "reason": item.get("reason"),
            }
            for item in relationships[:80]
        ],
    }
    system = (
        "You are the CAPITAL INDEX context-publisher-agent. "
        "Explain what an AI assistant would learn from this approved evidence bundle. "
        "Do not invent facts. Every substantive point must be grounded in source_evidence_ids. "
        "Write in clear Russian for the human owner. "
        "Return only valid JSON."
    )
    user = (
        "Create a human-readable bundle reading with this exact JSON shape:\n"
        "{"
        "\"executive_summary\": string, "
        "\"what_ai_learned\": [{\"point\": string, \"source_evidence_ids\": [string]}], "
        "\"key_themes\": [{\"theme\": string, \"why_it_matters\": string, \"source_evidence_ids\": [string]}], "
        "\"risks\": [{\"risk\": string, \"severity\": \"low|medium|high\", \"source_evidence_ids\": [string]}], "
        "\"open_questions\": [{\"question\": string, \"source_evidence_ids\": [string]}], "
        "\"recommended_next_actions\": [{\"action\": string, \"reason\": string, \"source_evidence_ids\": [string]}], "
        "\"source_evidence_ids\": [string], "
        "\"confidence\": number"
        "}\n\n"
        f"Bundle JSON:\n{json.dumps(compact_input, ensure_ascii=False)}"
    )
    return system, user


def normalize_bundle_reading(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "executive_summary": str(value.get("executive_summary") or "")[:4000],
        "what_ai_learned": _object_list(value.get("what_ai_learned"), ["point", "source_evidence_ids"], 20),
        "key_themes": _object_list(value.get("key_themes"), ["theme", "why_it_matters", "source_evidence_ids"], 20),
        "risks": _object_list(value.get("risks"), ["risk", "severity", "source_evidence_ids"], 20),
        "open_questions": _object_list(value.get("open_questions"), ["question", "source_evidence_ids"], 20),
        "recommended_next_actions": _object_list(
            value.get("recommended_next_actions"),
            ["action", "reason", "source_evidence_ids"],
            20,
        ),
        "source_evidence_ids": _string_list(value.get("source_evidence_ids"))[:100],
        "confidence": _confidence(value.get("confidence")),
    }


def parse_gemini_response(response: dict[str, Any]) -> dict[str, Any]:
    for candidate in response.get("candidates") or []:
        content = candidate.get("content") or {}
        for part in content.get("parts") or []:
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                parsed = json.loads(text)
                if not isinstance(parsed, dict):
                    raise ValueError("AI bundle reading JSON must be an object")
                return parsed
    raise ValueError("Gemini response did not include output JSON text")


def _object_list(value: Any, allowed_keys: list[str], limit: int) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    output = []
    for item in value[:limit]:
        if not isinstance(item, dict):
            continue
        normalized: dict[str, Any] = {}
        for key in allowed_keys:
            if key == "source_evidence_ids":
                normalized[key] = _string_list(item.get(key))[:20]
            else:
                normalized[key] = str(item.get(key) or "")[:1000]
        output.append(normalized)
    return output


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def _timeout_from_env() -> int:
    try:
        return max(1, int(os.environ.get("AI_READING_TIMEOUT_SECONDS", "90")))
    except ValueError:
        return 90
