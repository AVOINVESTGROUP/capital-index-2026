"""Authoritative Drive API metadata refetch for file upserts."""

from __future__ import annotations

import os
from typing import Any, Protocol


class DriveExecute(Protocol):
    def execute(self) -> dict[str, Any]:
        ...


class DriveFilesResource(Protocol):
    def get(self, **kwargs: Any) -> DriveExecute:
        ...


class DriveRevisionsResource(Protocol):
    def list(self, **kwargs: Any) -> DriveExecute:
        ...


class DriveService(Protocol):
    def files(self) -> DriveFilesResource:
        ...

    def revisions(self) -> DriveRevisionsResource:
        ...


DRIVE_FILE_FIELDS = (
    "id,"
    "owners(displayName,emailAddress,permissionId),"
    "capabilities,"
    "permissions(id,type,role,emailAddress,domain,deleted),"
    "headRevisionId,"
    "labelInfo"
)


def refetch_enabled_from_env() -> bool:
    return os.environ.get("DRIVE_REFETCH_ENABLED", "false").lower() == "true"


def _owner_summary(owner: dict[str, Any]) -> dict[str, Any]:
    return {
        "display_name": owner.get("displayName"),
        "email": owner.get("emailAddress"),
        "permission_id": owner.get("permissionId"),
    }


def _permissions_summary(permissions: list[dict[str, Any]]) -> dict[str, Any]:
    active = [item for item in permissions if not item.get("deleted")]
    by_role: dict[str, int] = {}
    by_type: dict[str, int] = {}
    external: list[dict[str, Any]] = []

    for item in active:
        role = item.get("role") or "unknown"
        permission_type = item.get("type") or "unknown"
        by_role[role] = by_role.get(role, 0) + 1
        by_type[permission_type] = by_type.get(permission_type, 0) + 1
        if permission_type in {"anyone", "domain"}:
            external.append(
                {
                    "type": permission_type,
                    "role": role,
                    "domain": item.get("domain"),
                }
            )

    return {
        "total": len(active),
        "by_role": by_role,
        "by_type": by_type,
        "external": external,
    }


def _head_revision_id(service: DriveService, file_id: str, file_metadata: dict[str, Any]) -> str | None:
    if file_metadata.get("headRevisionId"):
        return file_metadata.get("headRevisionId")

    response = service.revisions().list(
        fileId=file_id,
        fields="revisions(id,modifiedTime)",
        pageSize=1000,
    ).execute()
    revisions = response.get("revisions") or []
    if not revisions:
        return None
    return revisions[-1].get("id")


def fetch_authoritative_metadata(service: DriveService, file_id: str) -> dict[str, Any]:
    """Fetch authoritative metadata for one Drive file."""

    file_metadata = service.files().get(
        fileId=file_id,
        supportsAllDrives=True,
        fields=DRIVE_FILE_FIELDS,
    ).execute()
    permissions = file_metadata.get("permissions") or []
    return {
        "owners": [_owner_summary(owner) for owner in file_metadata.get("owners") or []],
        "head_revision_id": _head_revision_id(service, file_id, file_metadata),
        "drive_labels": file_metadata.get("labelInfo"),
        "capabilities": file_metadata.get("capabilities") or {},
        "permissions_summary": _permissions_summary(permissions),
    }


def apply_authoritative_metadata(upsert: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    """Return an upsert with authoritative Drive fields applied."""

    return {
        **upsert,
        "metadata_status": "authoritative_loaded",
        "authoritative_refetch_status": "loaded",
        "authoritative_fields": {
            "owners": metadata.get("owners"),
            "head_revision_id": metadata.get("head_revision_id"),
            "drive_labels": metadata.get("drive_labels"),
            "capabilities": metadata.get("capabilities"),
            "permissions_summary": metadata.get("permissions_summary"),
        },
    }


def refetch_authoritative_batch(
    batch: dict[str, Any],
    *,
    service: DriveService,
    refetch_enabled: bool,
) -> dict[str, Any]:
    """Refetch authoritative Drive metadata for file upserts when enabled."""

    upserts = batch.get("file_upserts") or []
    if not refetch_enabled:
        return {
            **batch,
            "authoritative_refetch": {
                "status": "disabled",
                "attempted": 0,
                "would_refetch": len(upserts),
            },
        }

    refetched: list[dict[str, Any]] = []
    attempted = 0
    loaded = 0
    failed = 0
    for upsert in upserts:
        file_id = (upsert.get("file") or {}).get("file_id")
        if not file_id or upsert.get("review_required"):
            refetched.append(upsert)
            continue
        attempted += 1
        try:
            metadata = fetch_authoritative_metadata(service, file_id)
            refetched.append(apply_authoritative_metadata(upsert, metadata))
            loaded += 1
        except Exception as exc:
            failed += 1
            refetched.append(
                {
                    **upsert,
                    "authoritative_refetch_status": "failed",
                    "review_required": True,
                    "review_reason": f"drive_refetch_failed:{type(exc).__name__}",
                    "next_action": "review_required",
                }
            )

    return {
        **batch,
        "file_upserts": refetched,
        "counts": {
            **(batch.get("counts") or {}),
            "review_required": sum(1 for item in refetched if item.get("review_required")),
        },
        "authoritative_refetch": {
            "status": "completed" if failed == 0 else "partial",
            "attempted": attempted,
            "loaded": loaded,
            "failed": failed,
        },
    }
