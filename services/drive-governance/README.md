# CAPITAL INDEX Drive Governance

Drive Governance evaluates whether Drive files are safe and useful enough to become AI evidence.

Current scope:

```text
local fixture evaluation
Cloud Run evaluation from Firestore /files + /extracted_text
controlled Firestore writes to /cleanup_queue and /file_duplicates when WRITE_ENABLED=true
no Drive mutation
no deletion
```

Implemented MVP detections:

```text
empty candidate
duplicate-name/hash candidate
stale/version candidate
unknown-project candidate
```

Run tests from repository root:

```text
python -m unittest services/drive-governance/tests/test_governance.py -v
```

Run fixture evaluation:

```text
python services/drive-governance/src/evaluate_governance.py tests/fixtures/drive-governance/file_inventory_governance_mvp.json
```

Cloud Run endpoints:

```text
GET /healthz
POST /evaluate-governance
```

Safe default:

```text
WRITE_ENABLED=false
```

With `WRITE_ENABLED=false`, the worker evaluates inventory and returns what it would write.
With `WRITE_ENABLED=true`, it writes only governance records:

```text
/cleanup_queue
/file_duplicates
```

It never mutates or deletes Drive files.
