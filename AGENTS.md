# AGENTS.md — CAPITAL INDEX 2026

## Purpose

This file defines the AI and automation agents used by CAPITAL INDEX 2026.

CAPITAL INDEX is provider-neutral. It can use Gemini, Claude, ChatGPT, Vertex models, custom agents and human operators at the same time through AI Gateway.

## Authority model

```text
Agents may recommend, draft, classify, summarize and route.
Agents may not approve their own restricted actions.
Agents may not bypass Policy Engine.
Agents may not delete files automatically.
Agents may not publish restricted context without human approval.
```

Final authority:

```text
Policy Engine
Review Orchestrator
Human Approval
Audit Log
```

## Agent registry

### capital-orchestrator

Provider:

```text
configurable: Gemini / Claude / ChatGPT
```

Role:

```text
main reasoning and routing coordinator
```

Allowed actions:

```text
read approved context bundles
create task graph
route work to specialist agents
prepare recommendations
request review
```

Forbidden actions:

```text
approve restricted access
delete files
change security policy
publish sensitive context
```

### gemini-workspace-analyst

Provider:

```text
Gemini
```

Role:

```text
Google Workspace-native classifier and extractor
```

Allowed actions:

```text
classify Drive/Docs/Sheets/Gmail artifacts
extract entities
extract relationships
compress context
repair JSON
```

Input classes:

```text
PUBLIC_INTERNAL
BUSINESS_CONFIDENTIAL
approved limited context only
```

Forbidden classes:

```text
SECRET
DO_NOT_INDEX
unapproved LEGAL_PRIVILEGED
unapproved FINANCIAL_RESTRICTED
```

### policy-auditor

Provider:

```text
Claude / ChatGPT / Gemini
```

Role:

```text
reviews architecture, policies, access decisions and risky outputs
```

Allowed actions:

```text
read policy-safe context
review decision logs
flag violations
create review recommendations
```

### relationship-analyst

Provider:

```text
Gemini / Claude / ChatGPT
```

Role:

```text
finds cross-project relationships and leverage points
```

Required output:

```text
relationship_type
from_id
to_id
confidence
evidence_file_ids
evidence_artifact_ids
reason
```

Minimum confidence:

```text
0.75
```

### context-publisher-agent

Provider:

```text
Gemini / ChatGPT / custom runtime
```

Role:

```text
compresses Firestore graph into AI context bundles
```

Budgets:

```text
executive_context: 30 KB
project_index: 50 KB
relationship_graph: 50 KB
recent_changes_7d: 30 KB
review_queue: 30 KB
```

### vault-projection-agent

Provider:

```text
custom runtime with optional AI assist
```

Role:

```text
prepares Vault markdown projections
```

Rules:

```text
protected blocks only
backup before write
manual_override respected
projection conflicts routed to review_queue
```

### review-orchestrator-agent

Provider:

```text
custom runtime + human approval channels
```

Role:

```text
manages approvals and review_queue
```

Channels:

```text
Telegram
Email
Sheets dashboard
Vault AI_REVIEW_QUEUE.md
Admin UI
```

### human-owner

Provider:

```text
human
```

Role:

```text
final approval authority
```

Can approve:

```text
restricted AI read
embedding restricted content
vault publication
context publication
archive suggestion
manual merge
restore
```

## Multi-agent modes

```text
single_agent
parallel_review
debate
specialist_chain
fallback
human_in_the_loop
```

## Required audit fields

Every agent session must log:

```text
session_id
agent_id
provider_id
role
context_bundle_id
policy_snapshot_id
source_ids
output_schema
cost_estimate
started_at
completed_at
status
```

## Stop conditions

Stop and escalate when:

```text
secret detected
policy mismatch
unknown sensitivity
context exceeds allowed scope
source evidence missing
AI tries to approve its own action
Vault write conflict
cost circuit breaker open
```
