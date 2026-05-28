from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from export_review_queue import ReviewItem, render_markdown, review_item_from_dict, sort_items


class ExportReviewQueueTest(unittest.TestCase):
    def test_review_item_from_dict_uses_defaults(self) -> None:
        item = review_item_from_dict(
            {
                "reason": "empty_text",
                "file_id": "file-123",
                "doc_title": "Probe Doc",
                "char_count": "1",
            },
            "review-123",
        )

        self.assertEqual(item.review_id, "review-123")
        self.assertEqual(item.status, "open")
        self.assertEqual(item.priority, "normal")
        self.assertEqual(item.char_count, 1)

    def test_sort_items_orders_by_priority_then_created_at(self) -> None:
        low = _item("review-low", priority="low", created_at="2026-05-27T12:00:00+00:00")
        high_late = _item("review-high-late", priority="high", created_at="2026-05-27T12:00:00+00:00")
        high_early = _item("review-high-early", priority="high", created_at="2026-05-27T11:00:00+00:00")

        sorted_ids = [item.review_id for item in sort_items([low, high_late, high_early])]

        self.assertEqual(sorted_ids, ["review-high-early", "review-high-late", "review-low"])

    def test_render_markdown_contains_table_and_details(self) -> None:
        markdown = render_markdown(
            [
                _item(
                    "review_bc5cc34df88fd73116047fca",
                    reason="empty_text",
                    file_id="1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM",
                    doc_title="drive-probe-test-001",
                )
            ],
            generated_at="2026-05-27T12:30:00+00:00",
            status_filter="open",
        )

        self.assertIn("# AI Review Queue", markdown)
        self.assertIn("| Priority | Status | Reason | Title | File | Updated |", markdown)
        self.assertIn("review_bc5cc34df88fd73116047fca", markdown)
        self.assertIn("empty_text", markdown)
        self.assertIn("drive-probe-test-001", markdown)
        self.assertIn("1PsAttUlqj30HTd79BK3cMBKTSVprvs9cU4jfPfgX0fM", markdown)


def _item(
    review_id: str,
    *,
    status: str = "open",
    priority: str = "normal",
    reason: str = "review_required",
    file_id: str = "file-123",
    doc_title: str = "Probe Doc",
    created_at: str = "2026-05-27T12:00:00+00:00",
) -> ReviewItem:
    return ReviewItem(
        review_id=review_id,
        status=status,
        priority=priority,
        reason=reason,
        file_id=file_id,
        doc_title=doc_title,
        sensitivity_class="PUBLIC_INTERNAL",
        source="content-extractor",
        source_collection="extracted_text",
        source_decision_id="policy-123",
        trace_id="trace-123",
        created_at=created_at,
        updated_at=created_at,
        next_action="human_review",
        char_count=1,
    )


if __name__ == "__main__":
    unittest.main()
