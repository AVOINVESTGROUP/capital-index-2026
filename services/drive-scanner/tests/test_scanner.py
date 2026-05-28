from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from drive_scanner.scanner import inventory_to_normalized_events, scan_drive


class FakeExecute:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response

    def execute(self) -> dict[str, Any]:
        return self.response


class FakeFiles:
    def __init__(self, by_folder: dict[str, list[dict[str, Any]]]) -> None:
        self.by_folder = by_folder

    def list(self, **kwargs: Any) -> FakeExecute:
        query = kwargs["q"]
        folder_id = query.split("'")[1]
        return FakeExecute({"files": self.by_folder.get(folder_id, [])})


class FakeDriveService:
    def __init__(self, by_folder: dict[str, list[dict[str, Any]]]) -> None:
        self._files = FakeFiles(by_folder)

    def files(self) -> FakeFiles:
        return self._files


class ScannerTest(unittest.TestCase):
    def test_scan_drive_walks_nested_folders_without_content_read(self) -> None:
        service = FakeDriveService(
            {
                "root": [
                    {
                        "id": "folder_child",
                        "name": "Child",
                        "mimeType": "application/vnd.google-apps.folder",
                    },
                    {
                        "id": "doc_1",
                        "name": "Doc",
                        "mimeType": "application/vnd.google-apps.document",
                    },
                ],
                "folder_child": [
                    {
                        "id": "sheet_1",
                        "name": "Sheet",
                        "mimeType": "application/vnd.google-apps.spreadsheet",
                    }
                ],
            }
        )

        inventory = scan_drive(service, root_folder_ids=["root"], max_files=10)

        self.assertEqual(inventory["counts"]["folders_seen"], 2)
        self.assertEqual([item["id"] for item in inventory["files"]], ["doc_1", "sheet_1"])

    def test_inventory_becomes_normalized_events(self) -> None:
        inventory = {
            "files": [
                {
                    "id": "doc_1",
                    "name": "Doc",
                    "mimeType": "application/vnd.google-apps.document",
                    "parents": ["root"],
                    "modifiedTime": "2026-05-27T00:00:00Z",
                    "webViewLink": "https://example.test",
                }
            ]
        }

        batch = inventory_to_normalized_events(
            inventory,
            gcp_project_id="capital-index-2026",
            project_id="capital_index",
            source_registry_id="drive_scan",
        )

        self.assertEqual(batch["schema_version"], "capital.normalized_drive_event_batch.v1")
        self.assertEqual(len(batch["events"]), 1)
        event = batch["events"][0]
        self.assertEqual(event["file_id"], "doc_1")
        self.assertEqual(event["file"]["mime_type"], "application/vnd.google-apps.document")


if __name__ == "__main__":
    unittest.main()
