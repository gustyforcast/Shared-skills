# Empirical Optimisation

Use execution evidence to improve card budgets without turning runtime noise into policy.

## Principles

1. **Execution telemetry is immutable evidence.** Record one execution as a separate `workflow-execution-telemetry/1` document derived from the exact canonical TaskSet and task ID.
2. **Failure-pattern correlation is association, not diagnosis.** Aggregate success/failure rates by card type, failure class and contract metrics. **Correlation is not causation.** Use the report to find candidates for review, not to infer mechanism.
3. **Budget proposals are gated.** A threshold may be proposed only when both adjacent metric values meet the configured **minimum sample** count and the higher value's failure rate exceeds the lower value by at least the configured delta.
4. **Never auto-apply** an empirical budget proposal. The analyser writes a proposal artefact; policy changes require explicit review and a separate policy file.
5. Prefer tightening over relaxing. A higher budget is not recommended automatically because successful outliers do not prove that a broader execution contract is safe.

## Telemetry contract

`record-telemetry` derives identity and complexity metrics from the canonical TaskSet. Do not hand-edit metrics to make a card look safer or riskier.

Required runtime facts: execution ID, timestamp, executor profile, result, duration and attempt. `FAILURE` requires a recognised failure class; `SUCCESS` must not carry one.

Metrics currently captured:

- output count;
- allowed-path count;
- dependency count;
- acceptance count;
- exact command-contract count;
- instruction character count;
- deterministic complexity score.

Telemetry is useful only when the exact TaskSet hash is retained.

## Analysis

`analyse-telemetry` validates every record, rejects duplicate execution IDs, sorts inputs deterministically, and emits counts/rates by:

- card type;
- failure class;
- each numeric contract metric.

Do not compare unpinned or structurally invalid telemetry.

## Budget proposal

The default policy lives in `templates/budget-policy.template.json`. `recommend-budgets` can propose a lower maximum for:

- `primary_outputs_max` from `output_count`;
- `allowed_paths_max` from `allowed_path_count`;
- `command_contracts_max` from `command_contract_count`.

A proposal records policy and analysis hashes, evidence counts and failure rates. It never edits the source policy.

Use a proposed policy only after explicit review, then pass it to `lint --policy <policy.json>` so the chosen budget is machine-enforced.
