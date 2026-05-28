from __future__ import annotations

import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from metadata_loader.drive_metadata import load_metadata_batch
from metadata_loader.drive_refetch import refetch_authoritative_batch


class FakeExecute:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def execute(self) -> dict:
        return self.payload


class FakeFiles:
    def __init__(self, service: "FakeDriveService") -> None:
        self.service = service

    def get(self, **kwargs) -> FakeExecute:
        self.service.file_calls.append(kwargs)
        return FakeExecute(
            {
                "id": kwargs["fileId"],
                "owners": [
                    {
                        "displayName": "Owner One",
                        "emailAddress": "owner@example.com",
                        "permissionId": "perm-owner",
                    }
                ],
                "headRevisionId": "head-rev-1",
                "capabilities": {"canEdit": True, "canComment": True},
                "permissions": [
                    {"id": "perm-owner", "type": "user", "role": "owner", "emailAddress": "owner@example.com"},
                    {"id": "perm-domain", "type": "domain", "role": "reader", "domain": "example.com"},
                ],
                "labelInfo": {"labels": []},
            }
        )


class FakeRevisions:
    def __init__(self, service: "FakeDriveService") -> None:
        self.service = service

    def list(self, **kwargs) -> FakeExecute:
        self.service.revision_calls.append(kwargs)
        return FakeExecute({"revisions": [{"id": "1"}, {"id": "2"}]})


class FakeDriveService:
    def __init__(self) -> None:
        self.file_calls: list[dict] = []
        self.revision_calls: list[dict] = []

    def files(self) -> FakeFiles:
        return FakeFiles(self)

    def revisions(self) -> FakeRevisions:
        return FakeRevisions(self)


class DriveRefetchTest(unittest.TestCase):
    def _batch(self) -> dict:
        fixture = (
            REPO_ROOT
            / "tests"
            / "fixtures"
            / "drive-events"
            / "normalized_probe_20260526T105738Z.json"
        )
        return load_metadata_batch(fixture)

    def test_refetch_disabled_does_not_call_drive(self) -> None:
        service = FakeDriveService()
        result = refetch_authoritative_batch(self._batch(), service=service, refetch_enabled=False)

        self.assertEqual(result["authoritative_refetch"]["status"], "disabled")
        self.assertEqual(service.file_calls, [])

    def test_refetch_enabled_loads_authoritative_fields(self) -> None:
        service = FakeDriveService()
        result = refetch_authoritative_batch(self._batch(), service=service, refetch_enabled=True)

        self.assertEqual(result["authoritative_refetch"]["status"], "completed")
        self.assertEqual(result["authoritative_refetch"]["loaded"], 1)
        self.assertEqual(len(service.file_calls), 1)
        self.assertEqual(service.revision_calls, [])

        upsert = result["file_upserts"][0]
        self.assertEqual(upsert["metadata_status"], "authoritative_loaded")
        self.assertEqual(upsert["authoritative_refetch_status"], "loaded")
        self.assertEqual(upsert["authoritative_fields"]["head_revision_id"], "head-rev-1")
        self.assertEqual(upsert["authoritative_fields"]["owners"][0]["email"], "owner@example.com")
        self.assertEqual(upsert["authoritative_fields"]["permissions_summary"]["by_type"]["domain"], 1)


if __name__ == "__main__":
    unittest.main()
