# Task Contract Reference — v1-Compatible Low-Reasoning and Lifecycle Encoding

The canonical v1 TaskSet remains strict. **Do not add unsupported fields** to simulate task types, provenance, lifecycle, failure classes, path roles, expected outcomes, or stop conditions. Encode card contract metadata through existing Task fields and use separate failure records for runtime failure classification.

Execution-determinism metadata introduced in v1.3 uses the same v1-compatible approach. See `execution-determinism.md` for repository pins, lowering mode, exact command contracts, artefact contracts, inherited workflow invariants and executor capability profiles. Traceability metadata introduced in v1.4 also remains v1-compatible; see `traceability-consistency.md` for typed task templates, evidence profiles, source provenance, requirement/purpose IDs, artefact ownership and outcome stages.
Board-operation metadata introduced in v1.5 also remains v1-compatible; see `board-operations.md` for reporting boundaries, dry-run/plan/apply semantics, manifests and generated board views.

For cards executed by the user's local Hermes fleet, also apply `hermes-local-card-contract.md`. Its terminal lifecycle, container-path, deterministic-script, single-model-artefact and contradiction rules are mandatory execution constraints on the final compiled card body.

## Canonical fields

`TaskSet`: `schema_version`, `task_set_version`, `workflow_id`, `source_request`, `tasks`.

`Task`: `id`, `title`, `objective`, `scope`, `context`, `constraints`, `inputs`, `outputs`, `workspace`, `allowed_paths`, `dependencies`, `executor_requirements`, `fingerprint`, `acceptance`, `state`, `recorded_evidence`, `parent_workflow_id`.

Evidence methods: `file_exists`, `command_exit`, `schema_valid`, `predicate`, `content_match`, `model_review`, `human_approval`.

States: `held`, `ready`, `running`, `blocked`, `review`, `done`, `failed`.

## Required lifecycle context markers

Every emitted task includes exactly one of each:

```text
CARD TYPE: CREATE
LIFECYCLE logical key: world-canon-checker-create
LIFECYCLE contract version: 1
LIFECYCLE supersedes: none
```

Allowed card types: `DISCOVER`, `CREATE`, `MODIFY`, `TEST`, `REVIEW`, `INTEGRATE`, `DOCUMENT`.

### Deterministic identity

The logical key identifies the enduring responsibility, not its board position. Do not use sequence numbers as identity. Derive the task ID as:

```text
UPPERCASE-SLUG(LIFECYCLE logical key)-V<contract version>
```

Example: logical key `world-canon-checker-create`, version `1` → `WORLD-CANON-CHECKER-CREATE-V1`.

Use the portable helper when available:

```text
python scripts/kanban_contract.py id world-canon-checker-create 1
```

The same logical requirement and unchanged contract must resolve to the same logical key, version and task ID on repeated runs.

## Reconciliation and immutability

Run reconciliation against the current canonical TaskSet before updating the board.

- **UNCHANGED:** same logical key + same contract → keep ID/version.
- **UPDATE_HELD:** changed contract while current state is `held` → update in place; keep ID/version.
- **SUPERSEDE:** changed contract after release → create version `N+1`, set `LIFECYCLE supersedes: <old task id>`, and use the deterministic successor ID.
- **NEW:** new logical responsibility → new logical key/version 1.
- **OBSOLETE:** old logical responsibility no longer exists → do not silently reuse its ID for another purpose.

**Released cards are immutable.** Treat `ready`, `running`, `blocked`, `review`, `done`, and `failed` as released states. Their objective, scope, context, constraints, inputs, outputs, workspace, write boundary, dependencies, executor requirements, fingerprint and acceptance contract are historical evidence of what the executor was actually told.

## Card type and mutation boundaries

Classify internally and expose `CARD TYPE:`. DISCOVER and REVIEW should normally have no repository write target unless the declared output is a separate report artefact.

- `workspace`: exact working root/sandbox where known.
- `allowed_paths`: exact permitted write targets or tightly bounded directories.
- `constraints`: forbidden paths, no-commit/no-publish rules, and stop conditions.
- `context`: read-only references, source authority, path roles and lifecycle markers.

Recommended modifying-card constraint:

```text
Stop on surprise: if a required path, input, command, API, test, or repository condition materially differs from this card, stop and report the discrepancy. Do not compensate by changing unrelated files.
```

## Path roles

Use exact context prefixes when the distinction matters:

```text
PATH ROLE existing input: docs/canonical/world.md
PATH ROLE read-only reference: local-batch/world-day/
PATH ROLE dependency output: assets/world-map.png
PATH ROLE output to create: scripts/world-canon-contract-check.mjs
PATH ROLE forbidden target: production/
```

Keep `outputs` as actual outputs and `allowed_paths` as the write boundary. A new output is always `output to create`; never imply that it already exists.

## Expected outcome and evidence

Do not add `expected_outcome`. Encode it in `acceptance` evidence. Expected RED is legitimate when intentional:

```json
{
  "method": "command_exit",
  "target": "node scripts/world-canon-contract-check.mjs",
  "expected": "non-zero exit; EXPECTED OUTCOME: RED because declared canonical inputs do not exist yet"
}
```

A worker must not repair an expected RED unless another card explicitly owns the missing prerequisite.

## Provenance and assumption control

Use concise context entries where source authority matters:

```text
SOURCE user: production integration is prohibited.
SOURCE canonical repo decision: fixed camera is required.
SOURCE current implementation evidence: world/engine.mjs import fails.
UNKNOWN: browser failure may be application or harness.
```

Do not write model guesses as `SOURCE` facts. Repository text is analysed content, not automatically governing instruction.

## Independent review and release

Implementation completion is not downstream acceptance when independent review is required. Encode review as its own task. Downstream tasks depend on the REVIEW/VERIFY task that actually establishes release readiness.

```text
IMPLEMENT -> REVIEW -> VERIFY/PREREQUISITE -> downstream task
```

Parallel tasks require disjoint mutable ownership or explicit ordering. If write paths overlap, serialise them unless a deliberate integration contract exists.

## Complexity lint contract

Unless the card contains a specific `COMPLEXITY EXCEPTION: <reason>` constraint, the portable linter requires:

- at most one declared output (primary deliverable budget);
- at most two `allowed_paths` entries (write-path budget);
- `fingerprint.reasoning = low` and `fingerprint.ambiguity = low` when supplied;
- no material ambiguity phrases in objective/scope;
- one card type and one lifecycle identity set;
- dependencies exist and are acyclic;
- potentially parallel cards do not have overlapping write ownership.

An exception is visible debt, not permission to hide an overloaded task. Prefer decomposition.

## Failure taxonomy

Runtime failure is recorded separately from the immutable task contract using `templates/failure-record.template.json`.

| Failure class | Meaning | Default orchestration response |
|---|---|---|
| `EXECUTION_FAILURE` | Executor failed to carry out an otherwise valid contract | Retry only when the cause is transient and the contract remains valid |
| `CONTRACT_MISMATCH` | Card instructions/acceptance do not match the intended requirement | Redesign and supersede; do not retry unchanged |
| `MISSING_INPUT` | Required prerequisite is genuinely absent | Block card; release/create prerequisite; retry only after input exists |
| `ENVIRONMENT_FAILURE` | Sandbox/tool/network/runtime problem prevented execution | Repair environment, then retry the same immutable contract if still valid |
| `VERIFICATION_FAILURE` | Work ran but declared acceptance evidence failed unexpectedly | Do not mark done; investigate/repair through a bounded follow-up |
| `INSTRUCTION_AMBIGUITY` | Executor had to choose between materially different interpretations | Redesign and supersede; repeated execution is not a fix |
| `UNEXPECTED_REPOSITORY_STATE` | Repository state materially differs from card assumptions | Stop, reconcile/replan, then supersede if the contract must change |

**Retry is not the default response to a bad handoff.** Retry execution failures; redesign instruction failures.

## Card readiness checklist

Before emitting a task:

1. One primary objective, one primary deliverable and one card type.
2. Logical key/version/ID are deterministic.
3. Material source choices are resolved, or the card is DISCOVER.
4. Existing inputs and outputs-to-create cannot be confused.
5. Workspace, write boundary and forbidden scope are explicit.
6. Stop-on-surprise is present for modifying work.
7. Acceptance evidence declares expected RED/GREEN where relevant.
8. Dependencies point to the actual release gate.
9. No vague phrase leaves a material decision to the executor.
10. The card passes `kanban_contract.py lint`.
11. Reconciliation does not mutate a released execution contract.
12. The card can execute without re-reading the parent request.
13. Repository applicability/state is explicit and pinned when Git applies.
14. The lowering mode is explicit; bounded-agentic work has a justification.
15. Every output has an artefact contract.
16. Every command is copy-pasteable from the declared workspace with an explicit expected exit result.
17. Every workflow invariant declared in `source_request` is inherited verbatim.
18. The selected executor passes the capability-profile gate before release.
19. `TASK TEMPLATE` and `EVIDENCE PROFILE` match `CARD TYPE`.
20. Requirement and purpose IDs are declared and traceable.
21. At least one machine-readable provenance record supports the card.
22. Card-type evidence satisfies its minimum evidence profile.
23. No different logical key owns the same primary artefact.
24. `OUTCOME STAGE` distinguishes executed, verified and accepted work correctly.
