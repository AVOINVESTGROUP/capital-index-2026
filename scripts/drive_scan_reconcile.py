from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "drive-scanner" / "src"))
sys.path.insert(0, str(REPO_ROOT / "services" / "metadata-loader" / "src"))

from drive_scanner.scanner import inventory_to_normalized_events, scan_drive
from metadata_loader.drive_metadata import load_metadata_payload
from metadata_loader.drive_refetch import refetch_authoritative_batch
from metadata_loader.firestore_writer import firestore_client, write_metadata_batch
from metadata_loader.workspace_auth import build_drive_service


def main() -> int:
    parser = argparse.ArgumentParser(description="Controlled Drive scan and /files reconciliation.")
    parser.add_argument("--root-folder-id", action="append", default=[])
    parser.add_argument("--max-files", type=int, default=25)
    parser.add_argument("--project-id", default="capital_index")
    parser.add_argument("--source-registry-id", default="drive_scan")
    parser.add_argument("--gcp-project-id", default="capital-index-2026")
    parser.add_argument("--database", default="(default)")
    parser.add_argument("--include-folders", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    root_folder_ids = args.root_folder_id or _env_roots()
    if not root_folder_ids:
        raise SystemExit("Provide --root-folder-id or DRIVE_SCAN_ROOT_FOLDER_IDS")

    drive_service = build_drive_service()
    inventory = scan_drive(
        drive_service,
        root_folder_ids=root_folder_ids,
        max_files=args.max_files,
        include_folders=args.include_folders,
    )
    event_batch = inventory_to_normalized_events(
        inventory,
        gcp_project_id=args.gcp_project_id,
        project_id=args.project_id,
        source_registry_id=args.source_registry_id,
    )
    metadata_batch = load_metadata_payload(event_batch, batch_ref="request://drive_scan_reconcile")
    metadata_batch = refetch_authoritative_batch(
        metadata_batch,
        service=drive_service,
        refetch_enabled=True,
    )
    client = firestore_client(args.gcp_project_id, args.database) if args.write else _NoopClient()
    write = write_metadata_batch(metadata_batch, client=client, write_enabled=args.write)

    print(
        json.dumps(
            {
                "write_enabled": args.write,
                "inventory_counts": inventory["counts"],
                "metadata_counts": metadata_batch["counts"],
                "write": write,
                "files": [
                    {
                        "file_id": (item.get("file") or {}).get("file_id"),
                        "name": (item.get("file") or {}).get("name"),
                        "mime_type": (item.get("file") or {}).get("mime_type"),
                        "metadata_status": item.get("metadata_status"),
                    }
                    for item in metadata_batch.get("file_upserts", [])[:20]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _env_roots() -> list[str]:
    raw = os.environ.get("DRIVE_SCAN_ROOT_FOLDER_IDS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


class _NoopClient:
    def collection(self, collection_name: str) -> Any:
        raise RuntimeError(f"Noop Firestore client cannot write collection {collection_name}")


if __name__ == "__main__":
    raise SystemExit(main())
