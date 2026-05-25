# QUALITY_GATES.md — CAPITAL INDEX 2026

## Purpose

This file defines quality gates that prevent CAPITAL INDEX from becoming a passive note dump or a weak second brain.

The system must not merely store user ideas. It must classify, challenge, route, connect and operationalize them.

## Gate 1 — No passive capture

Every captured idea must become a structured object.

Required fields:

```text
id
title
type
status
priority
owner
linked_projects
source
created_at
next_action
open_questions
```

If any field is missing, create a review item.

## Gate 2 — No fake path assumptions

Never invent file paths, project paths, Drive paths or Vault paths.

Required behavior:

```text
verify full parent chain
cite verified folder/file id internally
if path is not verified, mark as proposed_path, not actual_path
```

## Gate 3 — No AI-only truth

AI may summarize and propose. AI cannot make generated summaries canonical.

Canonical order:

```text
human decision
Firestore operational state
source file
BigQuery audit
Vault projection
AI summary
```

## Gate 4 — Every idea must be routed

Every strategic idea must be routed to one of:

```text
project_queue
strategic_opportunity
blocked_dependency
research_required
implementation_ready
archive
```

No idea remains only in chat.

## Gate 5 — Cross-project leverage detection

For every new idea, the system must check links to:

```text
CAPITAL INDEX
100Trust
Integra Motors
Fresh Cuisine
Content Factory
AVOuniverse
existing GCP/Firebase projects
Vault areas
```

Output must include:

```text
links_found
links_rejected
confidence
reason
```

## Gate 6 — Challenge before acceptance

For non-trivial ideas, the system must generate:

```text
strongest version
weakest point
required dependency
first validation step
reason not to do it now
```

## Gate 7 — Actionability

Every project artifact must end with exactly one operational next action.

Bad:

```text
think more
explore later
discuss
```

Good:

```text
create issue
write spec
verify API
create registry entry
run POC
```

## Gate 8 — Review queue over uncertainty

If the system is uncertain, it must create a review item instead of guessing.

Triggers:

```text
unknown source
unknown path
unknown sensitivity
conflicting project assignment
low confidence
missing evidence
manual override conflict
```

## Gate 9 — AI provider neutrality

No file or process may assume Claude, Gemini or ChatGPT as the only controlling AI.

Use:

```text
AI Gateway
ai_providers
ai_agents
context_bundles
```

## Gate 10 — User correction becomes rule

If the user corrects a structural mistake, convert the correction into a repository rule or quality gate.

Examples:

```text
wrong path assumption → Gate 2
missing AGENTS.md → mandatory root agent registry
missing GEMINI.md → mandatory provider instruction file
passive idea capture → Gate 1 and Gate 4
```
