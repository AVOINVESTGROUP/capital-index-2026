"""Enable AI context for already approved extracted text records.

This is a controlled migration helper. It only touches extracted_text rows whose
source file is already active, index eligible, not human-blocked, and extracted
text is not review-required. By default it only authorizes PUBLIC_INTERNAL text.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default="capital-index-2026")
    parser.add_argument("--database", default="(default)")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--write", action="store_true")
    parser.add_argument(
        "--allow-business-confidential",
        action="store_true",
        help="Also authorize BUSINESS_CONFIDENTIAL extracted text.",
    )
    args = parser.parse_args()

    token = access_token()
    base = (
        f"https://firestore.googleapis.com/v1/projects/{args.project}/databases/"
        f"{quote(args.database, safe='')}/documents"
    )
    files = {
        doc_id(doc): decode_map(doc.get("fields") or {}) | {"_doc_id": doc_id(doc)}
        for doc in list_collection(base, token, "files", args.limit)
    }
    extracted = [
        decode_map(doc.get("fields") or {}) | {"_doc_id": doc_id(doc)}
        for doc in list_collection(base, token, "extracted_text", args.limit)
    ]

    allowed_sensitivity = {"PUBLIC_INTERNAL"}
    if args.allow_business_confidential:
        allowed_sensitivity.add("BUSINESS_CONFIDENTIAL")

    candidates = []
    skipped = {"no_file": 0, "not_active": 0, "already_allowed": 0, "review_required": 0, "sensitivity": 0}
    for item in extracted:
        file_id = item.get("file_id") or item["_doc_id"]
        file_record = files.get(file_id)
        if not file_record:
            skipped["no_file"] += 1
            continue
        if item.get("ai_context_allowed") is True:
            skipped["already_allowed"] += 1
            continue
        if item.get("review_required") is True:
            skipped["review_required"] += 1
            continue
        if item.get("sensitivity_class") not in allowed_sensitivity:
            skipped["sensitivity"] += 1
            continue
        if not file_is_active(file_record):
            skipped["not_active"] += 1
            continue
        candidates.append({"file_id": file_id, "title": item.get("doc_title") or file_record.get("name") or file_id})

    if args.write:
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        for item in candidates:
            patch_document(
                base,
                token,
                "extracted_text",
                item["file_id"],
                {
                    "ai_context_allowed": {"booleanValue": True},
                    "ai_context_authorized_at": {"timestampValue": now},
                    "ai_context_authorized_by": {"stringValue": "enable_ai_context_for_active_extracted_rest"},
                    "ai_context_authorization_reason": {
                        "stringValue": "source file is active, index eligible, not human blocked, and text is public internal"
                    },
                },
                [
                    "ai_context_allowed",
                    "ai_context_authorized_at",
                    "ai_context_authorized_by",
                    "ai_context_authorization_reason",
                ],
            )

    print(
        json.dumps(
            {
                "write": args.write,
                "files_read": len(files),
                "extracted_read": len(extracted),
                "candidates": len(candidates),
                "skipped": skipped,
                "candidate_preview": candidates[:20],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def access_token() -> str:
    if os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN"):
        return os.environ["GOOGLE_OAUTH_ACCESS_TOKEN"].strip()
    gcloud = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not gcloud:
        raise RuntimeError("gcloud executable not found on PATH")
    for args in [
        [gcloud, "auth", "application-default", "print-access-token"],
        [gcloud, "auth", "print-access-token"],
    ]:
        try:
            return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()
        except subprocess.CalledProcessError:
            continue
    raise RuntimeError("Could not get gcloud access token")


def list_collection(base: str, token: str, collection: str, limit: int) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    page_token = ""
    while len(docs) < limit:
        params = {"pageSize": str(min(1000, limit - len(docs)))}
        if page_token:
            params["pageToken"] = page_token
        payload = request_json(f"{base}/{collection}?{urlencode(params)}", token)
        docs.extend(payload.get("documents") or [])
        page_token = payload.get("nextPageToken") or ""
        if not page_token:
            break
    return docs


def patch_document(
    base: str,
    token: str,
    collection: str,
    document_id: str,
    fields: dict[str, Any],
    update_mask: list[str],
) -> None:
    params = [("updateMask.fieldPaths", field) for field in update_mask]
    url = f"{base}/{collection}/{quote(document_id, safe='')}?{urlencode(params)}"
    request_json(url, token, method="PATCH", body={"fields": fields})


def request_json(url: str, token: str, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(url, data=data, method=method)
    request.add_header("authorization", f"Bearer {token}")
    if data is not None:
        request.add_header("content-type", "application/json")
    try:
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8") or "{}")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"Firestore request failed {exc.code}: {detail}") from exc


def doc_id(doc: dict[str, Any]) -> str:
    return str(doc.get("name") or "").split("/")[-1]


def decode_map(fields: dict[str, Any]) -> dict[str, Any]:
    return {key: decode_value(value) for key, value in fields.items()}


def decode_value(value: dict[str, Any]) -> Any:
    if "stringValue" in value:
        return value["stringValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return value["doubleValue"]
    if "booleanValue" in value:
        return value["booleanValue"]
    if "timestampValue" in value:
        return value["timestampValue"]
    if "nullValue" in value:
        return None
    if "arrayValue" in value:
        return [decode_value(item) for item in value["arrayValue"].get("values") or []]
    if "mapValue" in value:
        return decode_map(value["mapValue"].get("fields") or {})
    return None


def file_is_active(file_record: dict[str, Any]) -> bool:
    return (
        file_record.get("source_status") == "active"
        and file_record.get("index_eligible") is True
        and file_record.get("human_block") is not True
    )


if __name__ == "__main__":
    raise SystemExit(main())
