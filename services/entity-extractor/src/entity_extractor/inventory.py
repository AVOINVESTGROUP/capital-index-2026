"""Build entity extraction input from Firestore documents."""

from __future__ import annotations

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


def build_entity_input_from_firestore(
    *,
    client: FirestoreClient,
    limit: int,
    batch_ref: str = "firestore://extracted_text",
) -> dict[str, Any]:
    extracted_items: list[dict[str, Any]] = []
    file_records_by_id: dict[str, dict[str, Any]] = {}

    for snapshot in client.collection("extracted_text").limit(limit).stream():
        extracted_doc = snapshot.to_dict() or {}
        file_id = str(extracted_doc.get("file_id") or snapshot.id)
        extracted_items.append({**extracted_doc, "file_id": file_id})
        file_records_by_id[file_id] = (
            client.collection("files").document(file_id).get().to_dict() or {"file_id": file_id}
        )

    return {
        "extracted_batch": {
            "schema_version": "capital.extracted_text_batch.v1",
            "source": "firestore",
            "input_batch_ref": batch_ref,
            "extracted_text": extracted_items,
        },
        "file_records_by_id": file_records_by_id,
        "batch_ref": batch_ref,
    }
