# Execution Determinism — v1-Compatible Encoding

Use these rules to lower a validated workflow into executor-ready TaskSet v1 cards. **Do not add unsupported TaskSet fields.** Encode execution metadata through existing `context`, `constraints`, `workspace`, `executor_requirements`, `fingerprint`, `acceptance`, and `source_request` fields.

## Repository-state pinning

Every emitted card declares exactly one repository-state mode:

```text
REPOSITORY STATE: pinned
```

or:

```text
REPOSITORY STATE: not-applicable
REPOSITORY JUSTIFICATION: this workflow does not execute against a Git repository
```

A pinned card must also record:

```text
REPOSITORY root: C:\path\to\repo
REPOSITORY worktree: C:\path\to\worktree
REPOSITORY ref: branch-name-or-DETACHED
REPOSITORY head: 40-hex-commit-id
REPOSITORY dirty: clean
```

`REPOSITORY dirty:` is `clean` or `dirty`. The HEAD must be a hexadecimal Git object ID. Treat a material mismatch between the pin and execution state as `UNEXPECTED_REPOSITORY_STATE`; stop rather than improvising against a different checkout.

## Deterministic lowering

Before card emission, classify the executable work:

```text
Can the operation be encoded as a deterministic command/check?
  yes -> encode that command/check
  no  -> can the card writer resolve the material decision now?
          yes -> resolve it before card emission
          no  -> emit bounded agentic work or a DISCOVER/REVIEW card
```

Every card declares one of:

```text
LOWERING: deterministic
```

or:

```text
LOWERING: bounded-agentic
AGENTIC JUSTIFICATION: file contents require synthesis, but scope and acceptance are already fixed
```

`deterministic` requires `fingerprint.determinism: high` and `fingerprint.reasoning: low`. `bounded-agentic` requires exactly one non-empty `AGENTIC JUSTIFICATION:` and still must satisfy the normal low-reasoning budget.

## Exact command contracts

Use `acceptance[].evidence_requirements[]` with `method: command_exit` for executable commands. The `target` is the exact copy-pasteable command. `workspace` is the command working directory. `expected` states the expected exit result, for example:

```json
{
  "method": "command_exit",
  "target": "node scripts/world-canon-contract-check.mjs",
  "expected": "non-zero exit; EXPECTED OUTCOME: RED because required canonical inputs do not yet exist"
}
```

Do not emit phrases such as `run relevant tests`, `run appropriate checks`, or `use the usual command`. If exit status alone is insufficient, add `content_match`, `predicate`, `schema_valid`, or another explicit evidence requirement for the output condition.

## Artefact contracts

Every declared output has a contract in `context`:

```text
ARTEFACT CONTRACT: scripts/world-canon-contract-check.mjs | purpose=reject incomplete world-canon packages deterministically | required=checks declared paths and literals | prohibited=mutating repository files or fetching network resources
```

Each contract must identify the exact output path plus non-empty `purpose=`, `required=`, and `prohibited=` clauses. The path must match an item in `outputs` exactly. This is the semantic contract; `allowed_paths` remains the mutation boundary.

## Workflow invariants

Declare global invariants once in `source_request`, one per line:

```text
WORKFLOW INVARIANT WI-1: Do not modify files outside declared write boundaries.
WORKFLOW INVARIANT WI-2: Do not publish or deploy.
```

The compiler then copies them verbatim into every card as constraints:

```text
INHERITED INVARIANT WI-1: Do not modify files outside declared write boundaries.
INHERITED INVARIANT WI-2: Do not publish or deploy.
```

The portable linter rejects missing, altered, or undeclared inherited invariants. Use workflow invariants only for genuinely global rules; keep scoped restrictions on the affected cards.

## Executor capability profiles

Executor selection remains outside this skill. A capability profile only answers whether an already-selected executor can satisfy the card contract.

Profile shape:

```json
{
  "profile_id": "hermes-local-default",
  "capabilities": {
    "filesystem_read": true,
    "filesystem_write": true,
    "shell": true,
    "git": true,
    "browser": false,
    "network": false
  }
}
```

Validate before release:

```text
python scripts/kanban_contract.py check-capabilities <task-set.json> <executor-profile.json>
```

Every `executor_requirements` entry with `required: true` must resolve to `true` in the supplied profile. Missing capability keys fail closed. **Do not use the profile to choose a model provider.**
