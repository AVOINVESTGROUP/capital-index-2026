from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import google.auth
import google.auth.transport.requests
import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "drive-governance" / "src"))

from drive_governance.source_classifier import classify_batch  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply source classification via Firestore REST.")
    parser.add_argument("--project", default="capital-index-2026")
    parser.add_argument("--database", default="(default)")
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    token = _access_token()
    base = _base_url(args.project, args.database)
    files = _list_files(base, token, args.limit)
    result = classify_batch(files)
    changed = [item for item in result["decisions"] if _changed(item)]
    if args.write:
        for item in changed:
            _patch_file(base, token, item)
            _write_action(base, token, item)

    print(
        json.dumps(
            {
                "write_enabled": args.write,
                "counts": result["counts"],
                "write": {
                    "status": "written" if args.write else "disabled",
                    "updated": len(changed) if args.write else 0,
                    "would_update": len(changed),
                    "preserved": len(result["decisions"]) - len(changed),
                },
                "sample": [
                    {
                        "file_id": item["file_id"],
                        "name": item["name"],
                        "from": item["previous_source_status"],
                        "to": item["new_source_status"],
                        "eligible": item["new_index_eligible"],
                        "rule": item["rule_id"],
                    }
                    for item in changed[:25]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _access_token() -> str:
    try:
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        creds.refresh(google.auth.transport.requests.Request())
        return creds.token
    except Exception:
        gcloud = shutil.which("gcloud.cmd") or shutil.which("gcloud")
        if not gcloud:
            raise
        completed = subprocess.run(
            [gcloud, "auth", "print-access-token"],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()


def _base_url(project: str, database: str) -> str:
    return f"https://firestore.googleapis.com/v1/projects/{project}/databases/{database}/documents"


def _list_files(base: str, token: str, limit: int) -> list[dict[str, Any]]:
    response = requests.get(
        f"{base}/files",
        params={"pageSize": limit},
        headers=_headers(token),
        timeout=60,
    )
    response.raise_for_status()
    files = []
    for doc in response.json().get("documents") or []:
        fields = doc.get("fields") or {}
        file_id = doc["name"].split("/")[-1]
        files.append(_decode_map(fields) | {"file_id": _decode_value(fields.get("file_id")) or file_id})
    return files


def _patch_file(base: str, token: str, item: dict[str, Any]) -> None:
    params = [
        ("updateMask.fieldPaths", "source_status"),
        ("updateMask.fieldPaths", "index_eligible"),
        ("updateMask.fieldPaths", "human_block"),
        ("updateMask.fieldPaths", "source_quality_updated_at"),
        ("updateMask.fieldPaths", "source_quality_updated_by"),
        ("updateMask.fieldPaths", "source_quality_note"),
        ("updateMask.fieldPaths", "source_classification_rule_id"),
        ("updateMask.fieldPaths", "source_classification_confidence"),
    ]
    payload = {
        "fields": {
            "source_status": {"stringValue": item["new_source_status"]},
            "index_eligible": {"booleanValue": item["new_index_eligible"]},
            "human_block": {"booleanValue": item["new_human_block"]},
            "source_quality_updated_at": {"timestampValue": item["created_at"]},
            "source_quality_updated_by": {"stringValue": "source_classifier"},
            "source_quality_note": {"stringValue": f"auto rule: {item['rule_id']}"},
            "source_classification_rule_id": {"stringValue": item["rule_id"]},
            "source_classification_confidence": {"doubleValue": item["confidence"]},
        }
    }
    response = requests.patch(
        f"{base}/files/{item['file_id']}",
        params=params,
        headers={**_headers(token), "content-type": "application/json"},
        json=payload,
        timeout=60,
    )
    response.raise_for_status()


def _write_action(base: str, token: str, item: dict[str, Any]) -> None:
    action_id = f"source_rule_{item['file_id'][:16]}_{item['rule_id']}"
    payload = {
        "fields": {
            "schema_version": {"stringValue": "capital.source_quality_action.v1"},
            "action_id": {"stringValue": action_id},
            "file_id": {"stringValue": item["file_id"]},
            "actor_id": {"stringValue": "source_classifier"},
            "actor_type": {"stringValue": "automation"},
            "action": {"stringValue": "auto_classify"},
            "previous_source_status": {"stringValue": item["previous_source_status"]},
            "new_source_status": {"stringValue": item["new_source_status"]},
            "previous_index_eligible": {"booleanValue": item["previous_index_eligible"]},
            "new_index_eligible": {"booleanValue": item["new_index_eligible"]},
            "previous_human_block": {"booleanValue": item["previous_human_block"]},
            "new_human_block": {"booleanValue": item["new_human_block"]},
            "drive_mutation": {"stringValue": "none"},
            "drive_mutation_allowed": {"booleanValue": False},
            "policy_snapshot_id": {"stringValue": "source_classifier_rules_v2"},
            "note": {"stringValue": f"auto rule: {item['rule_id']}; confidence={item['confidence']}"},
            "created_at": {"timestampValue": item["created_at"]},
        }
    }
    response = requests.patch(
        f"{base}/source_quality_actions/{action_id}",
        headers={**_headers(token), "content-type": "application/json"},
        json=payload,
        timeout=60,
    )
    response.raise_for_status()


def _headers(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


def _decode_map(fields: dict[str, Any]) -> dict[str, Any]:
    return {key: _decode_value(value) for key, value in fields.items()}


def _decode_value(value: dict[str, Any] | None) -> Any:
    if not value:
        return None
    if "stringValue" in value:
        return value["stringValue"]
    if "booleanValue" in value:
        return value["booleanValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "timestampValue" in value:
        return value["timestampValue"]
    if "arrayValue" in value:
        return [_decode_value(item) for item in value["arrayValue"].get("values") or []]
    if "mapValue" in value:
        return _decode_map(value["mapValue"].get("fields") or {})
    return None


def _changed(item: dict[str, Any]) -> bool:
    return (
        item["previous_source_status"] != item["new_source_status"]
        or item["previous_index_eligible"] != item["new_index_eligible"]
        or item["previous_human_block"] != item["new_human_block"]
    )


if __name__ == "__main__":
    raise SystemExit(main())
