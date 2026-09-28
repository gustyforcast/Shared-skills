# Examples

## 1. Overloaded handoff → low-reasoning decomposition

### Overloaded handoff

Invalid even if self-contained:

> Interpret the world-canon plan, locate canonical sources, decide what is missing, create the checker and assets, run RED/GREEN validation, review the result, commit it, and prepare the next task.

The worker must make source-selection, sequencing, scope, verification and release decisions.

### Replacement workflow

The sequence is IMPLEMENT → REVIEW → prerequisite creation → VERIFY. The v1.2 card types remain CREATE/REVIEW/TEST; these phase labels preserve the intent of the earlier workflow.

**WORLD-CANON-CHECKER-CREATE-V1 — CREATE checker**

- `CARD TYPE: CREATE`
- `LIFECYCLE logical key: world-canon-checker-create`
- `LIFECYCLE contract version: 1`
- `LIFECYCLE supersedes: none`
- Objective: create `scripts/world-canon-contract-check.mjs` only.
- Context: `PATH ROLE output to create: scripts/world-canon-contract-check.mjs`.
- Constraint: **Do not look for this file; it is the output.**
- Run exactly `node scripts/world-canon-contract-check.mjs` once.
- Expected result: **Expected RED** because declared canonical inputs do not yet exist.
- Change no other file.

**WORLD-CANON-CHECKER-REVIEW-V1 — REVIEW checker**

Depends on CREATE. Read the checker/diff, verify literals and predicates, make no implementation edits, and return PASS/FAIL evidence.

**WORLD-CANON-INPUTS-CREATE-V1 — CREATE prerequisites**

Depends on REVIEW PASS. Creates only the missing canonical material owned by this card.

**WORLD-CANON-VERIFY-V1 — TEST final contract**

Depends on prerequisites. Runs the checker with expected GREEN. Downstream cards depend on VERIFY, not directly on CREATE.

## 2. Reconciliation and released-card immutability

Current card:

```text
ID: WORLD-CANON-CHECKER-CREATE-V1
logical key: world-canon-checker-create
version: 1
state: ready
```

A later thread changes the checker contract. Because the card was released, do **not** rewrite V1. Emit:

```text
ID: WORLD-CANON-CHECKER-CREATE-V2
LIFECYCLE logical key: world-canon-checker-create
LIFECYCLE contract version: 2
LIFECYCLE supersedes: WORLD-CANON-CHECKER-CREATE-V1
```

Reconciliation should report `SUPERSEDE`. If V1 were still `held`, the changed contract could be `UPDATE_HELD` in place with V1 identity preserved.

## 3. Failure class determines the response

A worker reports that PowerShell could not start because the sandbox runtime was unavailable. Record `ENVIRONMENT_FAILURE`; repair the environment and retry the same immutable card if its assumptions remain valid.

A worker invents a missing “world-canon-document” requirement because a new output was mistaken for an input. Record `INSTRUCTION_AMBIGUITY` or `CONTRACT_MISMATCH`; do not simply retry. Redesign the handoff and supersede the released card if necessary.

Expected RED is not `VERIFICATION_FAILURE` when RED was explicitly declared in acceptance.

## 4. Parallel join

- `DOC-INSTALL-MODIFY-V1`: update `docs/install.md` only.
- `DOC-API-EXAMPLES-MODIFY-V1`: update `docs/api-examples.md` only.
- They may run in parallel because mutable ownership is disjoint.
- `DOC-RELEASE-INDEX-INTEGRATE-V1` depends on both and updates only the release index.

If the two parallel tasks both write `docs/index.md`, lint must reject the write collision unless ordering is added.

## 5. Workflow invariant inheritance — Inherited prohibition

Parent requirement: update two recovery-copy components; never modify `world-day` or production. Declare the global rule once in `source_request`:

```text
WORKFLOW INVARIANT WI-1: Do not modify local-batch/world-day/** or production.
```

Every card then carries the mechanically inherited constraint:

```text
INHERITED INVARIANT WI-1: Do not modify local-batch/world-day/** or production.
```

Do not rely on the executor remembering the parent request.

## 6. Repository pin and deterministic lowering

A software card written against a known sandbox records the exact execution baseline:

```text
REPOSITORY STATE: pinned
REPOSITORY root: C:\HermesSandboxes\bof-world-a1-20260915
REPOSITORY worktree: C:\HermesSandboxes\bof-world-a1-20260915
REPOSITORY ref: recovery/world-canon
REPOSITORY head: 0123456789abcdef0123456789abcdef01234567
REPOSITORY dirty: clean
LOWERING: bounded-agentic
AGENTIC JUSTIFICATION: checker contents require code synthesis, but source choices and acceptance are fixed
```

A materially different checkout is `UNEXPECTED_REPOSITORY_STATE`, not permission to continue against the new state. A pure command-only TEST card should instead use `LOWERING: deterministic`.

## 7. Exact command contract and Artefact contract

Use the task `workspace` as the command working directory and make `command_exit.target` directly executable:

```text
node scripts/world-canon-contract-check.mjs
```

with an explicit result such as `non-zero exit; EXPECTED OUTCOME: RED ...`. Do not write `run relevant tests`.

The created output also carries:

```text
ARTEFACT CONTRACT: scripts/world-canon-contract-check.mjs | purpose=reject incomplete world-canon packages deterministically | required=checks declared paths and literals | prohibited=mutating repository files or fetching network resources
```

## 8. Executor capability profile gate

A selected Hermes executor may be represented by `templates/executor-profile.template.json`. Before release:

```text
python scripts/kanban_contract.py check-capabilities task-set.json executor-profile.json
```

If the card requires `shell: true` and the profile reports shell unavailable, the card is rejected. The profile checks capability only; it does not choose the model/provider.


## Traceability and consistency

A card begins with a declared trace chain rather than free-form prose:

```text
CARD TYPE: CREATE
TASK TEMPLATE: CREATE
EVIDENCE PROFILE: CREATE
REQUIREMENT ID: REQ-WORLD-CANON-001
PURPOSE ID: PURP-WORLD-CANON-001
PROVENANCE SRC-USER-001: type=user | locator=current-request | claim=create the checker before canonical inputs exist
OUTCOME STAGE: EXECUTED
```

The CREATE card proves execution with `file_exists` plus deterministic command evidence. A separate TEST card for the same requirement uses `TASK TEMPLATE: TEST`, `EVIDENCE PROFILE: TEST`, and `OUTCOME STAGE: VERIFIED`. A separate REVIEW card uses `TASK TEMPLATE: REVIEW`, `EVIDENCE PROFILE: REVIEW`, and `OUTCOME STAGE: ACCEPTED`. This is the explicit **executed → verified → accepted** chain; downstream release depends on the accepted gate, not merely the implementation card.

### Artefact ownership

`world-canon-checker-create` owns `scripts/world-canon-contract-check.mjs`. A different logical key must not declare that same output even if its card runs later. If another responsibility must combine changes into that artefact, create one explicit integration owner instead of shared mutation.

## 9. Board operation flow — dry-run → plan → apply

Before any board mutation, compare the current and proposed canonical TaskSets:

```text
python scripts/kanban_contract.py dry-run current.json proposed.json
python scripts/kanban_contract.py plan current.json proposed.json --output plan.json
```

The plan explains why each logical responsibility is NEW, UNCHANGED, UPDATE_HELD, SUPERSEDE or OBSOLETE. After review, `apply` writes a new canonical successor and regenerates JSON/CSV. The spreadsheet is a **generated view**, not a workflow source.

A CREATE card also states:

```text
REPORTING BOUNDARY: evidence-only
```

The worker returns declared evidence and exact discrepancies only; unrelated repository observations, speculative next steps and refactoring suggestions stay out of the execution report.
