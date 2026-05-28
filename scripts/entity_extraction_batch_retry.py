from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from google.cloud import firestore

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "entity-extractor" / "src"))

from entity_extractor.ai_provider import GeminiGenerateContentProvider, OpenAIResponsesProvider  # noqa: E402
from entity_extractor.firestore_writer import write_entity_extraction_batch  # noqa: E402
from entity_extractor.worker import build_entity_extraction_batch  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch entity extraction with retry for extracted text.")
    parser.add_argument("--project", default="capital-index-2026")
    parser.add_argument("--database", default="(default)")
    parser.add_argument("--provider", choices=["gemini", "openai"], default="gemini")
    parser.add_argument("--secret", default="capital-gemini-api-key")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-sleep", type=float, default=2.0)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    db = firestore.Client(project=args.project, database=args.database)
    extracted_items = _pending_extracted_items(db, args.limit, retry_failed=args.retry_failed)
    file_records_by_id = _file_records(db, [item["file_id"] for item in extracted_items])
    provider = _provider(
        args.provider,
        _secret_value(args.secret, args.project),
        args.model,
        args.timeout,
    )

    retrying_provider = _RetryingProvider(provider, retries=args.retries, retry_sleep=args.retry_sleep)
    batch = {
        "schema_version": "capital.extracted_text_batch.v1",
        "source": "entity_extraction_batch_retry",
        "input_batch_ref": "firestore://extracted_text/pending",
        "extracted_text": extracted_items,
    }
    result = build_entity_extraction_batch(
        batch,
        file_records_by_id,
        batch_ref="firestore://entity_extraction_batch_retry",
        ai_response_provider=retrying_provider.extract,
        provider_id=provider.provider_id,
        model_id=provider.model_id,
    )
    write = write_entity_extraction_batch(result, client=db, write_enabled=args.write)
    print(
        json.dumps(
            {
                "write_enabled": args.write,
                "input_extracted_text": len(extracted_items),
                "counts": result["counts"],
                "write": write,
                "files": [
                    {
                        "file_id": item.get("file_id"),
                        "name": file_records_by_id.get(item.get("file_id"), {}).get("name"),
                        "status": item.get("status"),
                        "entities": len(item.get("entities") or []),
                        "relationships": len(item.get("relationships") or []),
                        "issues": item.get("issues") or [],
                        "ai_provider_error": (item.get("ai_provider_error") or "")[:300],
                    }
                    for item in result["entity_extractions"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


class _RetryingProvider:
    def __init__(self, provider: Any, *, retries: int, retry_sleep: float) -> None:
        self.provider = provider
        self.retries = max(1, retries)
        self.retry_sleep = max(0.0, retry_sleep)

    def extract(self, candidate: dict[str, Any], extracted_text: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                return self.provider.extract(candidate, extracted_text)
            except Exception as exc:  # noqa: BLE001 - caller records provider failures.
                last_error = exc
                print(
                    f"retryable_provider_error file_id={candidate.get('file_id')} attempt={attempt}/{self.retries}: {exc}",
                    file=sys.stderr,
                    flush=True,
                )
                if attempt < self.retries and self.retry_sleep:
                    time.sleep(self.retry_sleep)
        raise RuntimeError(str(last_error) if last_error else "AI provider failed")


def _pending_extracted_items(
    db: firestore.Client,
    limit: int,
    *,
    retry_failed: bool,
) -> list[dict[str, Any]]:
    existing_by_file_id = _existing_entity_statuses(db)
    docs = db.collection("extracted_text").limit(1000).stream()
    items: list[dict[str, Any]] = []
    for doc in docs:
        data = doc.to_dict() or {}
        file_id = data.get("file_id") or doc.id
        existing_status = existing_by_file_id.get(file_id)
        if existing_status == "extracted":
            continue
        if existing_status and not retry_failed:
            continue
        if data.get("review_required") is True:
            continue
        if not (data.get("text") or "").strip():
            continue
        items.append(data | {"file_id": file_id})
        if len(items) >= limit:
            break
    return items


def _existing_entity_statuses(db: firestore.Client) -> dict[str, str]:
    result: dict[str, str] = {}
    for doc in db.collection("entity_extractions").limit(1000).stream():
        data = doc.to_dict() or {}
        file_id = data.get("file_id")
        if file_id:
            result[file_id] = data.get("status") or "unknown"
    return result


def _file_records(db: firestore.Client, file_ids: list[str]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for file_id in file_ids:
        data = db.collection("files").document(file_id).get().to_dict() or {}
        if data:
            records[file_id] = data | {"file_id": data.get("file_id") or file_id}
    return records


def _secret_value(secret_name: str, project_id: str) -> str:
    gcloud = shutil.which("gcloud.cmd") or shutil.which("gcloud")
    if not gcloud:
        raise RuntimeError("gcloud executable not found")
    completed = subprocess.run(
        [
            gcloud,
            "secrets",
            "versions",
            "access",
            "latest",
            "--secret",
            secret_name,
            "--project",
            project_id,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _provider(provider: str, api_key: str, model_id: str, timeout_seconds: int):
    if provider == "gemini":
        return GeminiGenerateContentProvider(
            api_key=api_key,
            model_id=model_id,
            timeout_seconds=timeout_seconds,
        )
    return OpenAIResponsesProvider(
        api_key=api_key,
        model_id=model_id or "gpt-5-mini",
        timeout_seconds=timeout_seconds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
