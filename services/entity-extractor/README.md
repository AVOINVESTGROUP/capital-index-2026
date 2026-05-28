# CAPITAL INDEX Entity Extractor

Entity extraction is not allowed to run on every extracted text document.

First gate:

```text
source_status = active
index_eligible = true
human_block = false
```

Blocked files produce an `entity_extraction_candidate` with:

```text
next_action: blocked
gate_reason: blocked_by_drive_governance
```

Allowed files produce:

```text
next_action: extract_entities
gate_reason: allowed
```

Current scope:

```text
Drive Governance source gate
provider-neutral AI prompt builder
AI JSON response normalizer
extracted entity/relationship contract
no live provider calls yet
no Firestore writes yet
no graph writes yet
```

Run tests:

```text
python -m unittest services/entity-extractor/tests/test_source_guard.py services/entity-extractor/tests/test_extraction.py services/entity-extractor/tests/test_schema_contracts.py -v
```
