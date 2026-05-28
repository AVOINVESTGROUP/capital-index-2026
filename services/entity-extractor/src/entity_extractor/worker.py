"""Entity extraction batch orchestration."""

from __future__ import annotations

from typing import Any, Callable

from entity_extractor.extraction import build_entity_extraction_result
from entity_extractor.source_guard import build_entity_candidates


def build_entity_extraction_batch(
    extracted_batch: dict[str, Any],
    file_records_by_id: dict[str, dict[str, Any]],
    *,
    batch_ref: str,
    ai_responses_by_file_id: dict[str, dict[str, Any]] | None = None,
    ai_response_provider: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None,
    provider_id: str = "manual_json",
    model_id: str = "not_called",
) -> dict[str, Any]:
    candidate_batch = build_entity_candidates(
        extracted_batch,
        file_records_by_id,
        batch_ref=batch_ref,
    )
    extracted_items_by_id = {
        item.get("file_id"): item for item in extracted_batch.get("extracted_text") or []
    }
    ai_responses = ai_responses_by_file_id or {}
    entity_extractions = []
    for candidate in candidate_batch["entity_extraction_candidates"]:
        extracted_item = extracted_items_by_id.get(candidate.get("file_id")) or {}
        ai_response = ai_responses.get(candidate.get("file_id"))
        if candidate.get("gate_allowed") is True and ai_response is None and ai_response_provider is not None:
            try:
                ai_response = ai_response_provider(candidate, extracted_item)
            except Exception as exc:  # noqa: BLE001 - provider failures become reviewable results.
                ai_response = {}
                extracted_item = {**extracted_item, "ai_provider_error": str(exc)}

        result = build_entity_extraction_result(
            candidate,
            extracted_item,
            ai_response,
            provider_id=provider_id,
            model_id=model_id,
        )
        if extracted_item.get("ai_provider_error"):
            result["issues"] = [*result["issues"], "ai_provider_error"]
            result["ai_provider_error"] = extracted_item["ai_provider_error"]
        entity_extractions.append(result)

    return {
        "schema_version": "capital.entity_extraction_batch.v1",
        "source": "entity_extractor",
        "input_batch_ref": batch_ref,
        "run_at": candidate_batch["run_at"],
        "counts": {
            "input_extracted_text": candidate_batch["counts"]["input_extracted_text"],
            "candidates": len(entity_extractions),
            "blocked": sum(1 for item in entity_extractions if item["status"] == "blocked"),
            "extracted": sum(1 for item in entity_extractions if item["status"] == "extracted"),
            "needs_review": sum(1 for item in entity_extractions if item["status"] == "needs_review"),
        },
        "entity_extraction_candidates": candidate_batch["entity_extraction_candidates"],
        "entity_extractions": entity_extractions,
    }
