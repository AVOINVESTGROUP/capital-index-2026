from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from google.cloud import firestore

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "entity-extractor" / "src"))

from entity_extractor.ai_provider import GeminiGenerateContentProvider, OpenAIResponsesProvider
from entity_extractor.firestore_writer import write_entity_extraction_batch
from entity_extractor.worker import build_entity_extraction_batch


def main() -> int:
    parser = argparse.ArgumentParser(description="Controlled live entity extraction probe.")
    parser.add_argument("--project", default="capital-index-2026")
    parser.add_argument("--database", default="(default)")
    parser.add_argument("--secret", default="capital-openai-api-key")
    parser.add_argument("--provider", choices=["openai", "gemini"], default="openai")
    parser.add_argument("--model", default="")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()

    api_key = _secret_value(args.secret, args.project)
    print("secret_loaded", file=sys.stderr, flush=True)
    db = firestore.Client(project=args.project, database=args.database)
    active_files = _active_files(db, args.limit)
    print(f"active_files={len(active_files)}", file=sys.stderr, flush=True)
    extracted_batch, file_records_by_id = _extracted_batch(db, active_files)
    print(f"extracted_text={len(extracted_batch['extracted_text'])}", file=sys.stderr, flush=True)

    provider = _provider(args.provider, api_key, args.model, args.timeout)
    print(f"provider={provider.provider_id} model={provider.model_id}", file=sys.stderr, flush=True)
    result = build_entity_extraction_batch(
        extracted_batch,
        file_records_by_id,
        batch_ref="firestore://live_entity_probe",
        ai_response_provider=provider.extract,
        provider_id=provider.provider_id,
        model_id=provider.model_id,
    )
    write_result = write_entity_extraction_batch(result, client=db, write_enabled=args.write)

    print(
        json.dumps(
            {
                "write_enabled": args.write,
                "write": write_result,
                "input_files": len(active_files),
                "counts": result["counts"],
                "files": [
                    {
                        "file_id": item["file_id"],
                        "name": file_records_by_id[item["file_id"]].get("name"),
                        "status": item["status"],
                        "entities": len(item["entities"]),
                        "relationships": len(item["relationships"]),
                        "issues": item["issues"],
                        "ai_provider_error": item.get("ai_provider_error", "")[:500],
                    }
                    for item in result["entity_extractions"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


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
            model_id=model_id or "gemini-2.0-flash",
            timeout_seconds=timeout_seconds,
        )
    return OpenAIResponsesProvider(
        api_key=api_key,
        model_id=model_id or "gpt-5-mini",
        timeout_seconds=timeout_seconds,
    )


def _active_files(db: firestore.Client, limit: int) -> list[dict[str, Any]]:
    docs = (
        db.collection("files")
        .where("source_status", "==", "active")
        .where("index_eligible", "==", True)
        .limit(limit)
        .stream()
    )
    return [doc.to_dict() | {"file_id": doc.to_dict().get("file_id") or doc.id} for doc in docs]


def _extracted_batch(
    db: firestore.Client,
    files: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    extracted_text: list[dict[str, Any]] = []
    file_records_by_id: dict[str, dict[str, Any]] = {}
    for file_record in files:
        file_id = file_record["file_id"]
        extracted = db.collection("extracted_text").document(file_id).get().to_dict() or {}
        if not extracted:
            continue
        extracted_text.append(extracted | {"file_id": file_id})
        file_records_by_id[file_id] = file_record

    return (
        {
            "schema_version": "capital.extracted_text_batch.v1",
            "source": "firestore_live_probe",
            "input_batch_ref": "firestore://live_entity_probe",
            "extracted_text": extracted_text,
        },
        file_records_by_id,
    )


if __name__ == "__main__":
    raise SystemExit(main())
