"""Seed baseline Firestore configuration for CAPITAL INDEX 2026.

Run from repository root after Firebase/Firestore baseline is ready:

    python scripts/seed_firestore_baseline.py

Required local auth:

    gcloud auth application-default login
    gcloud auth application-default set-quota-project capital-index-2026
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore

PROJECT_ID = "capital-index-2026"
VAULT_ROOT_FOLDER_ID = "1No6LMuCpH2T2jmGL7hnFlMto-0gnnHpq"
DRIVE_EVENT_TEST_FOLDER_ID = "1YHJ0YY4I_8QulKJR2O5S972_BK93NqMu"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def set_doc(db: firestore.Client, path: str, data: dict[str, Any]) -> None:
    collection, document = path.rsplit("/", 1)
    ref = db.collection(collection).document(document)
    payload = {
        **data,
        "updated_at": now_iso(),
        "seeded_by": "scripts/seed_firestore_baseline.py",
    }
    ref.set(payload, merge=True)
    print(f"seeded {path}")


def main() -> None:
    db = firestore.Client(project=PROJECT_ID, database="(default)")

    set_doc(
        db,
        "system_config/model_routing",
        {
            "fast_classifier": "UNSET",
            "deep_extractor": "UNSET",
            "embedding_model": "UNSET",
            "long_context_model": "UNSET",
            "status": "placeholder_until_model_ids_selected",
        },
    )

    set_doc(
        db,
        "system_config/vector_backend",
        {
            "active_backend": "firestore",
            "allowed_backends": ["firestore", "bigquery", "vertex_vector_search"],
            "firestore": {
                "max_dimensions": 2048,
                "max_result_count": 1000,
                "usage": "operational_dedupe_and_small_scale_semantic_search",
            },
            "bigquery": {
                "usage": "analytics_vector_search_and_large_scale_history",
            },
            "vertex_vector_search": {
                "usage": "large_scale_low_latency_retrieval",
                "enabled": False,
            },
        },
    )

    set_doc(
        db,
        "system_config/throttling",
        {
            "ai_calls_per_minute_limit": 100,
            "ai_calls_current_window": 0,
            "document_ai_pages_per_hour_limit": 500,
            "embedding_calls_per_minute_limit": 300,
            "backfill_concurrency": 5,
            "interactive_concurrency": 20,
            "circuit_state": "closed",
            "cooldown_until": None,
        },
    )

    set_doc(
        db,
        "project_registry/capital_index",
        {
            "project_id": "capital_index",
            "display_name": "CAPITAL INDEX 2026",
            "type": "control_plane",
            "status": "active_setup",
            "gcp_project_id": PROJECT_ID,
            "firebase_project_ids": [PROJECT_ID],
            "drive_root_folder_ids": [VAULT_ROOT_FOLDER_ID, DRIVE_EVENT_TEST_FOLDER_ID],
            "vault_path": "00-Vault/",
            "sensitivity_default": "BUSINESS_CONFIDENTIAL",
            "owner": "alexander",
            "priority": "critical",
            "enabled": True,
        },
    )

    set_doc(
        db,
        "source_registry/vault_root",
        {
            "source_id": "vault_root",
            "source_type": "google_drive_folder",
            "project_id": "capital_index",
            "business_area": "capital_index",
            "drive_file_id": VAULT_ROOT_FOLDER_ID,
            "canonical": True,
            "data_domain": "vault",
            "sensitivity_class": "BUSINESS_CONFIDENTIAL",
            "indexing_enabled": True,
            "embedding_allowed": True,
            "ai_summary_allowed": True,
            "vault_publish_allowed": False,
        },
    )

    set_doc(
        db,
        "source_registry/drive_event_test",
        {
            "source_id": "drive_event_test",
            "source_type": "google_drive_folder",
            "project_id": "capital_index",
            "business_area": "capital_index",
            "drive_file_id": DRIVE_EVENT_TEST_FOLDER_ID,
            "canonical": False,
            "data_domain": "poc",
            "sensitivity_class": "PUBLIC_INTERNAL",
            "indexing_enabled": True,
            "embedding_allowed": False,
            "ai_summary_allowed": False,
            "vault_publish_allowed": False,
        },
    )

    set_doc(
        db,
        "security_policies/default_locked",
        {
            "policy_id": "default_locked",
            "description": "Default locked policy for unknown or unclassified resources.",
            "sensitivity_class": "UNCLASSIFIED_REVIEW_REQUIRED",
            "allowed_actions": ["read_metadata"],
            "denied_actions": [
                "read_content",
                "summarize",
                "embed",
                "publish_to_vault",
                "include_in_ai_context",
            ],
            "approval_required_for": ["read_content", "summary", "embedding", "context_publish"],
        },
    )

    set_doc(
        db,
        "folder_policies/vault_root",
        {
            "folder_id": VAULT_ROOT_FOLDER_ID,
            "policy_name": "Vault Root Baseline",
            "project_id": "capital_index",
            "sensitivity_class": "BUSINESS_CONFIDENTIAL",
            "inherit_to_children": True,
            "allowed_actions": ["read_metadata", "read_content", "summarize", "embed"],
            "denied_actions": ["publish_restricted_context"],
            "approval_required_for": [],
        },
    )

    set_doc(
        db,
        "folder_policies/drive_event_test",
        {
            "folder_id": DRIVE_EVENT_TEST_FOLDER_ID,
            "policy_name": "Drive Events POC Test Folder",
            "project_id": "capital_index",
            "sensitivity_class": "PUBLIC_INTERNAL",
            "inherit_to_children": True,
            "allowed_actions": ["read_metadata", "read_content"],
            "denied_actions": ["embed", "publish_to_vault", "include_in_ai_context"],
            "approval_required_for": [],
        },
    )

    print("Firestore baseline seed complete.")


if __name__ == "__main__":
    main()
