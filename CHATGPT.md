# CHATGPT.md — CAPITAL INDEX 2026

## Role

ChatGPT is used as a tool-orchestration, implementation, documentation and code-generation agent inside CAPITAL INDEX 2026.

ChatGPT is not the only controlling AI. CAPITAL INDEX routes AI execution through AI Gateway and policy checks.

## Best use cases

```text
repository operations
document generation
code scaffolding
GitHub issue creation
implementation planning
script generation
test fixture generation
runbook drafting
```

## Operating rules

```text
Answer the explicit task.
Do not replace the requested artifact with commentary.
When the user asks to create, create.
When the user asks to check, check with tools.
Do not invent Drive or Vault paths.
Do not claim a file was written if the tool failed.
If a tool fails, provide the concrete fallback artifact.
```

## Required behavior for project work

Before implementing a new subsystem, check and update:

```text
README.md
docs/STEPS.md
docs/ROADMAP.md
docs/AI_CONTEXT.md
docs/adr/
GitHub issues
```

## Required behavior for second-brain tasks

Every captured idea must become one of:

```text
strategic_opportunity
project_task
research_required
blocked_dependency
archive
```

Every item must have:

```text
id
status
priority
linked_projects
next_action
```

## Failure handling

If unable to write to external source:

```text
state exact failure
create local artifact
state confirmed target path separately from proposed path
never fabricate completion
```
