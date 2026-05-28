"""Live AI provider adapters for entity extraction."""

from __future__ import annotations

import json
import os
from typing import Any, Protocol

import requests

from entity_extractor.extraction import build_entity_extraction_prompt
from entity_extractor.secret_manager import gemini_api_key_from_env, openai_api_key_from_env


class EntityAIProvider(Protocol):
    provider_id: str
    model_id: str

    def extract(self, candidate: dict[str, Any], extracted_text: dict[str, Any]) -> dict[str, Any]:
        ...


class DisabledAIProvider:
    provider_id = "disabled"
    model_id = "not_called"

    def extract(self, candidate: dict[str, Any], extracted_text: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("AI provider is disabled")


class OpenAIResponsesProvider:
    provider_id = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model_id: str,
        endpoint: str = "https://api.openai.com/v1/responses",
        timeout_seconds: int = 60,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required")
        if not model_id:
            raise ValueError("OpenAI model id is required")
        self.api_key = api_key
        self.model_id = model_id
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def extract(self, candidate: dict[str, Any], extracted_text: dict[str, Any]) -> dict[str, Any]:
        prompt = build_entity_extraction_prompt(candidate, extracted_text)
        response = requests.post(
            self.endpoint,
            headers={
                "authorization": f"Bearer {self.api_key}",
                "content-type": "application/json",
            },
            json={
                "model": self.model_id,
                "input": [
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]},
                ],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "capital_entity_extraction",
                        "strict": True,
                        "schema": ai_response_schema(),
                    }
                },
            },
            timeout=self.timeout_seconds,
        )
        if not response.ok:
            raise RuntimeError(f"OpenAI Responses API failed: {response.status_code} {response.text}")

        return parse_openai_response(response.json())


class GeminiGenerateContentProvider:
    provider_id = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model_id: str,
        endpoint_base: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_seconds: int = 60,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key is required")
        if not model_id:
            raise ValueError("Gemini model id is required")
        self.api_key = api_key
        self.model_id = model_id
        self.endpoint_base = endpoint_base.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def extract(self, candidate: dict[str, Any], extracted_text: dict[str, Any]) -> dict[str, Any]:
        prompt = build_entity_extraction_prompt(candidate, extracted_text)
        return self.generate_json(system=prompt["system"], user=prompt["user"])

    def generate_json(self, *, system: str, user: str) -> dict[str, Any]:
        response = requests.post(
            f"{self.endpoint_base}/models/{self.model_id}:generateContent",
            headers={
                "content-type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            json={
                "system_instruction": {
                    "parts": [{"text": system}],
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": user}],
                    }
                ],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0,
                },
            },
            timeout=self.timeout_seconds,
        )
        if not response.ok:
            raise RuntimeError(f"Gemini generateContent failed: {response.status_code} {response.text}")

        return parse_gemini_response(response.json())


def ai_provider_enabled_from_env() -> bool:
    return os.environ.get("AI_PROVIDER_ENABLED", "false").lower() == "true"


def provider_from_env() -> EntityAIProvider:
    if not ai_provider_enabled_from_env():
        return DisabledAIProvider()

    return configured_provider_from_env()


def configured_provider_from_env() -> EntityAIProvider:
    provider = os.environ.get("AI_PROVIDER", "openai").lower()
    if provider == "gemini":
        return GeminiGenerateContentProvider(
            api_key=gemini_api_key_from_env(),
            model_id=os.environ.get("GEMINI_MODEL_ID", "gemini-2.0-flash").strip(),
            endpoint_base=os.environ.get(
                "GEMINI_ENDPOINT_BASE",
                "https://generativelanguage.googleapis.com/v1beta",
            ),
            timeout_seconds=_timeout_from_env(),
        )

    if provider != "openai":
        raise ValueError(f"Unsupported AI_PROVIDER: {provider}")

    return OpenAIResponsesProvider(
        api_key=openai_api_key_from_env(),
        model_id=os.environ.get("OPENAI_MODEL_ID", "").strip(),
        endpoint=os.environ.get("OPENAI_RESPONSES_ENDPOINT", "https://api.openai.com/v1/responses"),
        timeout_seconds=_timeout_from_env(),
    )


def parse_openai_response(response: dict[str, Any]) -> dict[str, Any]:
    output_text = response.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return _json_object(output_text)

    for output_item in response.get("output") or []:
        for content_item in output_item.get("content") or []:
            text = content_item.get("text")
            if isinstance(text, str) and text.strip():
                return _json_object(text)

    raise ValueError("OpenAI response did not include output JSON text")


def parse_gemini_response(response: dict[str, Any]) -> dict[str, Any]:
    for candidate in response.get("candidates") or []:
        content = candidate.get("content") or {}
        for part in content.get("parts") or []:
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                return _json_object(text)

    raise ValueError("Gemini response did not include output JSON text")


def ai_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["entities", "relationships"],
        "properties": {
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["type", "name", "confidence", "evidence_text", "attributes"],
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": [
                                "PROJECT",
                                "COMPANY",
                                "PERSON",
                                "ASSET",
                                "DOCUMENT",
                                "TASK",
                                "DATE",
                                "MONEY",
                                "LOCATION",
                                "OTHER",
                            ],
                        },
                        "name": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "evidence_text": {"type": "string"},
                        "attributes": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {},
                        },
                    },
                },
            },
            "relationships": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "relationship_type",
                        "from_id",
                        "to_id",
                        "confidence",
                        "evidence_file_ids",
                        "evidence_artifact_ids",
                        "reason",
                    ],
                    "properties": {
                        "relationship_type": {"type": "string"},
                        "from_id": {"type": "string"},
                        "to_id": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0.75, "maximum": 1},
                        "evidence_file_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "evidence_artifact_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "reason": {"type": "string"},
                    },
                },
            },
        },
    }


def _json_object(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("AI response JSON must be an object")
    return parsed


def _timeout_from_env() -> int:
    try:
        return max(1, int(os.environ.get("AI_PROVIDER_TIMEOUT_SECONDS", "60")))
    except ValueError:
        return 60
