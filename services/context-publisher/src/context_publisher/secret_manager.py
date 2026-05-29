"""Secret Manager access for context-publisher AI providers."""

from __future__ import annotations

import os
from functools import lru_cache


@lru_cache(maxsize=16)
def access_secret_version(secret_name: str, *, project_id: str) -> str:
    from google.cloud import secretmanager

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8").strip()


def gemini_api_key_from_env() -> str:
    direct = os.environ.get("GEMINI_API_KEY", "").strip()
    if direct:
        return direct

    secret_name = os.environ.get("GEMINI_API_KEY_SECRET_NAME", "").strip()
    if not secret_name:
        return ""

    return access_secret_version(
        secret_name,
        project_id=os.environ.get("GCP_PROJECT_ID", "capital-index-2026"),
    )
