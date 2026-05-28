from __future__ import annotations

import json
import sys
from pathlib import Path

from googleapiclient.discovery import build

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "content-extractor" / "src"))

from content_extractor.workspace_auth import workspace_credentials


def main() -> int:
    creds = workspace_credentials(["https://www.googleapis.com/auth/drive.readonly"])
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    queries = [
        (
            "markdown",
            "trashed=false and (name contains '.md' or mimeType='text/markdown' or mimeType='text/plain')",
        ),
        (
            "sheets",
            "trashed=false and mimeType='application/vnd.google-apps.spreadsheet'",
        ),
    ]
    for label, query in queries:
        print(f"## {label}")
        response = (
            service.files()
            .list(
                q=query,
                spaces="drive",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                pageSize=10,
                fields="files(id,name,mimeType,modifiedTime,webViewLink,parents)",
            )
            .execute()
        )
        files = response.get("files", [])
        if not files:
            print("(none)")
        for file_obj in files:
            print(json.dumps(file_obj, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
