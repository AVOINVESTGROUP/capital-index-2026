"""Build Drive Governance inventory from Firestore documents."""

from __future__ import annotations

import hashlib
from typing import Any, Protocol


class Snapshot(Protocol):
    id: str

    def to_dict(self) -> dict[str, Any] | None:
        ...


class DocumentRef(Protocol):
    def get(self) -> Snapshot:
        ...


class CollectionRef(Protocol):
    def document(self, document_id: str) -> DocumentRef:
        ...

    def limit(self, count: int) -> "CollectionRef":
        ...

    def stream(self) -> list[Snapshot]:
        ...


class FirestoreClient(Protocol):
    def collection(self, collection_name: str) -> CollectionRef:
        ...


def build_inventory_from_firestore(
    *,
    client: FirestoreClient,
    limit: int,
    fixture_id: str = "firestore_inventory",
) -> dict[str, Any]:
    files = []
    for snapshot in client.collection("files").limit(limit).stream():
        file_doc = snapshot.to_dict() or {}
        file_id = str(file_doc.get("file_id") or snapshot.id)
        extracted_doc = client.collection("extracted_text").document(file_id).get().to_dict() or {}
        files.append(_inventory_file(file_id, file_doc, extracted_doc))

    return {
        "schema_version": "capital.drive_governance_inventory.v1",
        "fixture_id": fixture_id,
        "files": files,
    }


def _inventory_file(file_id: str, file_doc: dict[str, Any], extracted_doc: dict[str, Any]) -> dict[str, Any]:
    text = str(extracted_doc.get("text") or "")
    char_count = _first_int(extracted_doc.get("char_count"), len(text) if text else None)
    non_whitespace = _first_int(
        extracted_doc.get("non_whitespace_char_count"),
        sum(1 for char in text if not char.isspace()) if text else None,
    )

    return {
        "file_id": file_id,
        "name": file_doc.get("name") or "",
        "mime_type": file_doc.get("mime_type"),
        "parents": file_doc.get("parents") or [],
        "trashed": bool(file_doc.get("trashed", False)),
        "modified_time": file_doc.get("modified_time"),
        "created_time": file_doc.get("created_time"),
        "size": _first_int(file_doc.get("size"), extracted_doc.get("size")),
        "web_view_link": file_doc.get("web_view_link"),
        "gcp_project_id": file_doc.get("gcp_project_id"),
        "project_id": file_doc.get("project_id"),
        "source_registry_id": file_doc.get("source_registry_id"),
        "source_status": file_doc.get("source_status"),
        "index_eligible": file_doc.get("index_eligible"),
        "human_block": file_doc.get("human_block"),
        "source_approved_by": file_doc.get("source_approved_by"),
        "source_quality_updated_by": file_doc.get("source_quality_updated_by"),
        "text_stats": {
            "char_count": char_count,
            "non_whitespace_char_count": non_whitespace,
            "text_hash": extracted_doc.get("text_hash") or _text_hash(text),
        },
    }


def _first_int(*values: Any) -> int | None:
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def _text_hash(text: str) -> str | None:
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
