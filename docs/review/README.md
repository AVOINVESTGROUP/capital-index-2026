# Review Queue Projection

Firestore `/review_queue` is the source of truth.

`AI_REVIEW_QUEUE.md` is a generated operator view for open review items:

```text
python scripts/export_review_queue.py --status open --output docs/review/AI_REVIEW_QUEUE.md
```

Use this projection to see what needs human attention before the system continues with restricted or unclear content.
