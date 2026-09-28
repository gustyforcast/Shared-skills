# Hermes Local Card Contract

This is the canonical execution contract for cards sent to the user's local Hermes fleet. It applies to review, evidence and implementation cards authored through `workflow-to-kanban`, `hermes-kanban-delegate`, archive salvage, or any successor workflow.

The Windows host may be used by the controller for repository discovery and provenance. Once a card is executed inside a Hermes worker/reviewer sandbox, its actionable paths and lifecycle instructions must follow this contract.

## Non-negotiable invariants

1. **Exactly one terminal lifecycle call.** Every worker/reviewer run must make exactly one of `kanban_complete`, `kanban_block`, `kanban_request_review`, or `kanban_request_changes`, then stop. A downstream controller closing the card does not waive this requirement.
2. **Do not present a lifecycle menu to the model.** Preselect one exact terminal action, or have the deterministic script return one machine-readable `lifecycle_action` that the model invokes once.
3. **Sandbox paths are container paths.** Actionable read/write paths inside the card use only `/workspace`, `/evidence`, or `/reports`. Never instruct a sandboxed model to write to `C:\...` or another Windows host path.
4. **One model-authored verdict/result artefact.** For review/evidence work, the model writes exactly one verdict file under `/reports`. Deterministic scripts may write machine-readable evidence under `/evidence`; those files are not extra model-authored reports.
5. **One bounded model job.** The model runs the declared deterministic script, reads its machine-readable result, writes the one declared verdict/result artefact, makes the one terminal lifecycle call, and stops.
6. **Contradictions invalidate the card.** Reject instructions such as `do not call a lifecycle tool`, multiple lifecycle alternatives, Windows sandbox write targets, or multiple model-authored evidence reports.
## Review and evidence card shape

Use this pattern for local review/evidence profiles, including `gpt-oss-20b` review work:

```text
Objective: <one bounded review question>

Run exactly one deterministic reviewer script as the first substantive tool call:
python /evidence/<card-id>/run_review_checks.py

Do not call search_files, read_file, list_directory, skills, pwd, ls, git, todo or any other discovery command before that runner.

Read its machine-readable result:
/evidence/<card-id>/review-result.json

The model writes exactly one verdict file:
/reports/<card-id>.verdict.json

Then make exactly one terminal lifecycle call specified by lifecycle_action in the machine-readable result.
Stop immediately after that lifecycle call.

Do not create any other model-authored report.
Do not write to a Windows path from the sandbox.
```

The deterministic script owns evidence gathering, comparisons, hashing and repeatable checks. The model owns only the bounded verdict interpretation and the single lifecycle invocation. Do not ask the model to reconcile many raw tool results itself.
## Implementation worker shape

Implementation cards may modify the one bounded declared change-set under `/workspace`. Keep the acceptance path deterministic:

```text
Objective: <one bounded implementation outcome>

Modify only the declared paths under /workspace.
Run exactly one deterministic acceptance script:
<exact command under /workspace or /evidence>

Read the machine-readable acceptance result.
Write exactly one worker result/verdict artefact under /workspace/reports or /reports, according to the qualified profile mount contract.

Then make exactly one terminal lifecycle call specified by the card or by lifecycle_action in the deterministic result.
Stop immediately after that lifecycle call.
```

Do not widen the implementation scope to compensate for unexpected repository state. Use the standard stop-on-surprise boundary.

## Host-path provenance

A Windows path may appear only as non-actionable provenance when it is necessary to identify where the controller obtained evidence. It must never be phrased as a sandbox write target, working directory, output path, or command argument that the worker is expected to execute.

## Validation gate

Before dispatching a Hermes card, save its final body to a local temporary file and run:

```powershell
python scripts/validate_hermes_card.py path\to\card.md
```

Run this from the `workflow-to-kanban` skill directory, or invoke the script by its full host path. A non-zero exit means rewrite the card; do not dispatch it.

The TaskSet-level `kanban_contract.py lint` gate still applies. The Hermes card validator is an additional execution-contract gate, not a replacement for TaskSet linting.
