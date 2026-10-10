---
name: compressing-prompts-for-local-models
description: Use when converting a complex instruction, workflow, or agent task into a short deterministic prompt for a smaller or local model with limited memory, reasoning, or tool reliability.
---

# Compressing Prompts For Local Models

Move judgement upstream. The local model should execute a bounded contract, not rediscover the plan.

## Procedure

1. Extract the single primary objective. Split independent objectives instead of combining them into one prompt.
2. Resolve source selection, scope, paths, formats, constraints and acceptance rules before writing the prompt whenever the surrounding context provides the answers.
3. Replace references such as "that file", "the usual format" or "fix it" with literal names, paths, values or observable conditions.
4. Separate inputs from outputs. Label read-only inputs, allowed write targets and forbidden targets explicitly.
5. Remove background explanation that does not change the next action. Preserve facts needed to choose correctly.
6. Convert subjective completion language into evidence: exact file, required fields, command, count, hash, screenshot or other observable result.
7. State forbidden inference where guessing would be harmful. Missing required input should produce `BLOCKED`, not an invented substitute.
8. Keep one clear stopping point. Do not ask the local model to keep improving indefinitely.

Use this order:

```text
ROLE
OBJECTIVE
INPUTS
TASK
OUTPUT
FORBIDDEN
SUCCESS
STOP
```

## Evidence and output

Return one copy-paste prompt, followed by a short note only when an assumption or unresolved dependency must be visible to the user.

Prefer exact verbs such as read, compare, create, replace, run and report. Avoid "as needed", "where appropriate", "use your judgement", "make it better" and other open-ended delegation.

Do not add capabilities the target model or profile does not have. Do not turn a planning question into permission to modify files, run external actions, deploy, publish or commit.
