# Board Operations — Canonical Authority and Generated Views

## Canonical authority

**Canonical TaskSet is the authority.** Reconciliation compares canonical TaskSet JSON to canonical TaskSet JSON. A spreadsheet, CSV, Kanban JSON file or UI board is a **Derived view** and must never become reconciliation input or acquire independent requirements, dependencies, acceptance state or executor instructions.

Every generated view carries the canonical TaskSet SHA-256 and a `do_not_edit` notice. To change work, edit/recompile the canonical TaskSet, then rerender the board.

## Reporting boundaries

Every card declares exactly one machine-readable boundary:

```text
REPORTING BOUNDARY: evidence-only
```

Supported policies:

- `evidence-only` — return declared evidence, exact discrepancies and failure classification only. Use for CREATE, MODIFY, TEST, INTEGRATE and DOCUMENT; it is also the compatibility-safe minimum for other templates.
- `evidence-and-findings` — DISCOVER may return bounded findings needed to resolve its declared unknown, but not design alternatives or unrelated observations.
- `verdict-and-evidence` — REVIEW may return the acceptance verdict plus supporting evidence, but not speculative next steps or unrelated refactors.

Each card also carries one `Reporting boundary:` constraint. Do not report design alternatives, speculative next steps, unrelated repository observations or refactoring suggestions unless a separate card explicitly asks for them.

## dry-run → plan → apply

Board operations are fail-closed and directional:

1. **dry-run** — lint current/proposed TaskSets and reconcile them. Produce console diagnostics only. **NO FILES WRITTEN.**
2. **plan** — write an explainable reconciliation report. Each action records its logical key, prior/proposed IDs, whether the contract changed, and why the action is NEW, UNCHANGED, UPDATE_HELD, SUPERSEDE or OBSOLETE. This does not apply the workflow.
3. **apply** — after successful reconciliation, write a **new canonical successor file** and regenerate its manifest and derived board views. Never overwrite either reconciliation input. Inputs remain audit evidence.

Portable commands:

```text
python scripts/kanban_contract.py dry-run current.json proposed.json
python scripts/kanban_contract.py plan current.json proposed.json --output plan.json
python scripts/kanban_contract.py apply current.json proposed.json --canonical-out canonical-next.json --manifest-out manifest.json --board-json-out board.json --csv-out cards.csv
```

`reconcile` remains available for the compact legacy text report. `plan` is the richer machine-readable form.

## Workflow manifest

Generate a deterministic manifest from valid canonical TaskSet JSON:

```text
python scripts/kanban_contract.py manifest task-set.json --output manifest.json
```

The manifest records at minimum:

- workflow/task-set identity;
- canonical TaskSet SHA-256;
- task, state and card-type counts;
- requirement/purpose IDs;
- inherited workflow invariants;
- accepted release gates;
- declared allowed and forbidden write paths;
- `board_is_derived: true`.

It is a summary, not a second workflow specification.

## Safe board rendering

Render spreadsheet-ready views only from validated canonical TaskSet JSON:

```text
python scripts/kanban_contract.py render-board task-set.json --json board.json --csv cards.csv
```

The JSON/CSV include `generated_view`, `source_taskset_sha256` and `do_not_edit`. They expose card identity, state, traceability, reporting boundary, workspace, write paths and dependencies for board use, but the canonical TaskSet remains authoritative.

Never patch a generated CSV/board to fix the workflow. Repair the canonical TaskSet and regenerate the view.
