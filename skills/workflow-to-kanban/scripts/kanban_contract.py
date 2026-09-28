#!/usr/bin/env python3
"""Deterministic lifecycle and complexity checks for workflow-to-kanban TaskSet v1.

This tool does not replace the repository's canonical schema validator. It adds
portable skill-layer checks that can be applied before board/CSV compilation.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

CARD_TYPES = {"DISCOVER", "CREATE", "MODIFY", "TEST", "REVIEW", "INTEGRATE", "DOCUMENT"}
FAILURE_CLASSES = {
    "EXECUTION_FAILURE",
    "CONTRACT_MISMATCH",
    "MISSING_INPUT",
    "ENVIRONMENT_FAILURE",
    "VERIFICATION_FAILURE",
    "INSTRUCTION_AMBIGUITY",
    "UNEXPECTED_REPOSITORY_STATE",
}
RELEASED_STATES = {"ready", "running", "blocked", "review", "done", "failed"}
AMBIGUOUS_PHRASES = (
    "relevant files",
    "as needed",
    "where appropriate",
    "fix any issues",
    "ensure it works",
    "use your judgement",
    "use your judgment",
    "etc.",
)
MODIFYING_TYPES = {"CREATE", "MODIFY", "INTEGRATE", "DOCUMENT"}
REPOSITORY_STATES = {"pinned", "not-applicable"}
LOWERING_MODES = {"deterministic", "bounded-agentic"}
VAGUE_COMMAND_PHRASES = (
    "run relevant tests",
    "run appropriate tests",
    "run relevant checks",
    "run appropriate checks",
    "use the usual command",
    "as needed",
)
OUTCOME_STAGE_BY_TYPE = {
    "DISCOVER": "EXECUTED",
    "CREATE": "EXECUTED",
    "MODIFY": "EXECUTED",
    "TEST": "VERIFIED",
    "REVIEW": "ACCEPTED",
    "INTEGRATE": "EXECUTED",
    "DOCUMENT": "EXECUTED",
}
REPORTING_BOUNDARIES_BY_TYPE = {
    "DISCOVER": {"evidence-only", "evidence-and-findings"},
    "CREATE": {"evidence-only"},
    "MODIFY": {"evidence-only"},
    "TEST": {"evidence-only"},
    "REVIEW": {"evidence-only", "verdict-and-evidence"},
    "INTEGRATE": {"evidence-only"},
    "DOCUMENT": {"evidence-only"},
}

EVIDENCE_PROFILE_RULES = {
    "DISCOVER": {"all": set(), "any": {"content_match", "predicate", "model_review", "human_approval"}},
    "CREATE": {"all": {"file_exists"}, "any": {"command_exit", "schema_valid", "content_match", "predicate"}},
    "MODIFY": {"all": set(), "any": {"command_exit", "schema_valid", "content_match", "predicate"}},
    "TEST": {"all": {"command_exit"}, "any": set()},
    "REVIEW": {"all": set(), "any": {"model_review", "human_approval", "predicate"}},
    "INTEGRATE": {"all": {"command_exit"}, "any": set()},
    "DOCUMENT": {"all": {"file_exists"}, "any": {"content_match", "schema_valid", "predicate"}},
}

DEFAULT_BUDGET_POLICY = {
    "schema_version": "workflow-budget-policy/1",
    "policy_id": "default-v1",
    "thresholds": {
        "primary_outputs_max": 1,
        "allowed_paths_max": 2,
        "command_contracts_max": 3,
    },
    "evidence_gate": {
        "minimum_samples_per_value": 10,
        "minimum_failure_rate_delta": 0.15,
        "direction": "tighten-only",
    },
}
TELEMETRY_RESULTS = {"SUCCESS", "FAILURE"}
TELEMETRY_METRICS = (
    "output_count",
    "allowed_path_count",
    "dependency_count",
    "acceptance_count",
    "command_contract_count",
    "instruction_chars",
    "complexity_score",
)
THRESHOLD_METRIC_MAP = {
    "primary_outputs_max": "output_count",
    "allowed_paths_max": "allowed_path_count",
    "command_contracts_max": "command_contract_count",
}


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _context_values(task: dict[str, Any], prefix: str) -> list[str]:
    return [
        item[len(prefix) :].strip()
        for item in task.get("context", [])
        if isinstance(item, str) and item.startswith(prefix)
    ]


def _single_context(task: dict[str, Any], prefix: str) -> str | None:
    values = _context_values(task, prefix)
    return values[0] if len(values) == 1 else None


def _workflow_invariants(payload: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    invariants: dict[str, str] = {}
    errors: list[str] = []
    source = str(payload.get("source_request", ""))
    pattern = re.compile(r"^WORKFLOW INVARIANT ([A-Za-z0-9_.-]+):\s*(.+)$")
    for line in source.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        key, text = match.group(1), match.group(2).strip()
        if key in invariants:
            errors.append(f"Duplicate workflow invariant id {key!r}.")
        elif not text:
            errors.append(f"Workflow invariant {key!r} must have non-empty text.")
        else:
            invariants[key] = text
    return invariants, errors


def _declared_source_items(payload: dict[str, Any], label: str) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    errors: list[str] = []
    source = str(payload.get("source_request", ""))
    pattern = re.compile(rf"^{re.escape(label)} ([A-Za-z0-9_.-]+):\s*(.+)$")
    for line in source.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        key, text = match.group(1), match.group(2).strip()
        if key in values:
            errors.append(f"Duplicate {label.lower()} id {key!r}.")
        elif not text:
            errors.append(f"{label.title()} {key!r} must have non-empty text.")
        else:
            values[key] = text
    return values, errors


def _provenance_records(task: dict[str, Any]) -> tuple[list[dict[str, str]], list[str]]:
    records: list[dict[str, str]] = []
    errors: list[str] = []
    pattern = re.compile(
        r"^PROVENANCE ([A-Za-z0-9_.-]+):\s*type=([^|]+)\|\s*locator=([^|]+)\|\s*claim=(.+)$"
    )
    seen: set[str] = set()
    for item in task.get("context", []):
        if not isinstance(item, str) or not item.startswith("PROVENANCE "):
            continue
        match = pattern.match(item.strip())
        if not match:
            errors.append(
                f"Malformed provenance {item!r}; expected 'PROVENANCE <id>: type=<type> | locator=<locator> | claim=<claim>'."
            )
            continue
        source_id, source_type, locator, claim = [part.strip() for part in match.groups()]
        if source_id in seen:
            errors.append(f"Duplicate provenance id {source_id!r}.")
            continue
        seen.add(source_id)
        if not source_type or not locator or not claim:
            errors.append(f"Provenance {source_id!r} requires non-empty type=, locator= and claim= values.")
            continue
        records.append({"id": source_id, "type": source_type, "locator": locator, "claim": claim})
    return records, errors


def _evidence_methods(task: dict[str, Any]) -> set[str]:
    methods: set[str] = set()
    for acceptance in task.get("acceptance", []):
        if not isinstance(acceptance, dict):
            continue
        for evidence in acceptance.get("evidence_requirements", []):
            if isinstance(evidence, dict) and isinstance(evidence.get("method"), str):
                methods.add(evidence["method"])
    return methods


def _normalise_path_value(path: str) -> str:
    return path.replace("\\", "/").rstrip("/").lower()


def _artefact_contracts(task: dict[str, Any]) -> tuple[dict[str, dict[str, str]], list[str]]:
    contracts: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    prefix = "ARTEFACT CONTRACT:"
    for item in task.get("context", []):
        if not isinstance(item, str) or not item.startswith(prefix):
            continue
        raw = item[len(prefix):].strip()
        parts = [part.strip() for part in raw.split("|")]
        path = parts[0] if parts else ""
        fields: dict[str, str] = {}
        for part in parts[1:]:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            fields[key.strip().lower()] = value.strip()
        if not path:
            errors.append("Artefact contract is missing an output path.")
            continue
        if path in contracts:
            errors.append(f"Duplicate artefact contract for {path!r}.")
            continue
        for required in ("purpose", "required", "prohibited"):
            if not fields.get(required):
                errors.append(f"Artefact contract for {path!r} is missing non-empty {required}= clause.")
        contracts[path] = fields
    return contracts, errors


def _required_capabilities(task: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for req in task.get("executor_requirements", []):
        if isinstance(req, dict) and req.get("required") is True and isinstance(req.get("capability"), str):
            result.add(req["capability"])
    return result


def logical_key(task: dict[str, Any]) -> str | None:
    return _single_context(task, "LIFECYCLE logical key:")


def contract_version(task: dict[str, Any]) -> int | None:
    raw = _single_context(task, "LIFECYCLE contract version:")
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value >= 1 else None


def supersedes(task: dict[str, Any]) -> str | None:
    return _single_context(task, "LIFECYCLE supersedes:")


def card_type(task: dict[str, Any]) -> str | None:
    value = _single_context(task, "CARD TYPE:")
    return value.upper() if value else None


def slug_logical_key(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-").upper()
    slug = re.sub(r"-+", "-", slug)
    if not slug:
        raise ValueError("logical key produces an empty task id")
    return slug


def expected_task_id(key: str, version: int) -> str:
    return f"{slug_logical_key(key)}-V{version}"


def has_complexity_exception(task: dict[str, Any]) -> bool:
    return any(
        isinstance(x, str) and x.startswith("COMPLEXITY EXCEPTION:")
        for x in task.get("constraints", [])
    )


def _path_overlap(a: str, b: str) -> bool:
    x, y = _normalise_path_value(a), _normalise_path_value(b)
    if not x or not y:
        return False
    return x == y or x.startswith(y + "/") or y.startswith(x + "/")


def _dependency_reachability(tasks: list[dict[str, Any]]) -> dict[str, set[str]]:
    deps = {task.get("id"): set(task.get("dependencies", [])) for task in tasks}
    reach: dict[str, set[str]] = {k: set() for k in deps if k}

    def visit(task_id: str, seen: set[str]) -> set[str]:
        out: set[str] = set()
        for dep in deps.get(task_id, set()):
            if dep in seen:
                continue
            out.add(dep)
            out.update(visit(dep, seen | {dep}))
        return out

    for task_id in list(reach):
        reach[task_id] = visit(task_id, {task_id})
    return reach


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def taskset_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _write_json(path: str | Path, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def reporting_boundary(task: dict[str, Any]) -> str | None:
    value = _single_context(task, "REPORTING BOUNDARY:")
    return value.lower() if value else None


def _latest_by_logical_key(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for task in payload.get("tasks", []):
        key = logical_key(task)
        ver = contract_version(task) or 0
        if key is None:
            continue
        if key not in result or ver > (contract_version(result[key]) or 0):
            result[key] = task
    return result


def reconcile_details(current: dict[str, Any], proposed: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    errors, actions = reconcile(current, proposed)
    if errors:
        return errors, []
    old = _latest_by_logical_key(current)
    new = _latest_by_logical_key(proposed)
    details: list[dict[str, Any]] = []
    for action_line in actions:
        action = action_line.split(" ", 1)[0]
        key_match = re.search(r"logical_key=([^\s]+)", action_line)
        key = key_match.group(1) if key_match else ""
        previous = old.get(key)
        candidate = new.get(key)
        changed = bool(previous and candidate and _normalised_contract(previous) != _normalised_contract(candidate))
        reasons = {
            "NEW": "logical responsibility is absent from the current TaskSet and present in the proposal",
            "OBSOLETE": "logical responsibility is present in the current TaskSet and absent from the proposal",
            "UNCHANGED": "logical responsibility and normalised execution contract are unchanged",
            "UPDATE_HELD": "held card contract changed before release and may be updated in place",
            "SUPERSEDE": "released card contract changed; immutable history requires a versioned successor",
        }
        details.append({
            "action": action,
            "logical_key": key,
            "previous_id": previous.get("id") if previous else None,
            "proposed_id": candidate.get("id") if candidate else None,
            "previous_state": previous.get("state") if previous else None,
            "contract_changed": changed,
            "reason": reasons.get(action, "reconciliation action derived from canonical TaskSet comparison"),
        })
    return [], details


def workflow_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    workflow_invariants, _ = _workflow_invariants(payload)
    state_counts: dict[str, int] = {}
    card_type_counts: dict[str, int] = {}
    requirement_ids: set[str] = set()
    purpose_ids: set[str] = set()
    accepted_gate_ids: list[str] = []
    allowed_paths: set[str] = set()
    forbidden_paths: set[str] = set()
    for task in payload.get("tasks", []):
        state = str(task.get("state", ""))
        state_counts[state] = state_counts.get(state, 0) + 1
        ctype = card_type(task) or "UNKNOWN"
        card_type_counts[ctype] = card_type_counts.get(ctype, 0) + 1
        req = _single_context(task, "REQUIREMENT ID:")
        purp = _single_context(task, "PURPOSE ID:")
        if req:
            requirement_ids.add(req)
        if purp:
            purpose_ids.add(purp)
        if _single_context(task, "OUTCOME STAGE:") == "ACCEPTED":
            accepted_gate_ids.append(str(task.get("id")))
        for path in task.get("allowed_paths", []):
            allowed_paths.add(str(path))
        for item in task.get("context", []):
            if isinstance(item, str) and item.startswith("PATH ROLE forbidden target:"):
                forbidden_paths.add(item.split(":", 1)[1].strip())
    return {
        "schema_version": "workflow-manifest/1",
        "generated_from": "canonical-taskset",
        "board_is_derived": True,
        "workflow_id": payload.get("workflow_id"),
        "task_set_version": payload.get("task_set_version"),
        "taskset_sha256": taskset_sha256(payload),
        "task_count": len(payload.get("tasks", [])),
        "state_counts": dict(sorted(state_counts.items())),
        "card_type_counts": dict(sorted(card_type_counts.items())),
        "requirement_ids": sorted(requirement_ids),
        "purpose_ids": sorted(purpose_ids),
        "workflow_invariants": dict(sorted(workflow_invariants.items())),
        "accepted_gate_ids": sorted(accepted_gate_ids),
        "allowed_write_paths": sorted(allowed_paths),
        "forbidden_paths": sorted(forbidden_paths),
    }


def board_view(payload: dict[str, Any]) -> dict[str, Any]:
    source_hash = taskset_sha256(payload)
    cards: list[dict[str, Any]] = []
    for task in payload.get("tasks", []):
        cards.append({
            "id": task.get("id"),
            "title": task.get("title"),
            "state": task.get("state"),
            "card_type": card_type(task),
            "requirement_id": _single_context(task, "REQUIREMENT ID:"),
            "purpose_id": _single_context(task, "PURPOSE ID:"),
            "outcome_stage": _single_context(task, "OUTCOME STAGE:"),
            "reporting_boundary": reporting_boundary(task),
            "objective": task.get("objective"),
            "workspace": task.get("workspace"),
            "allowed_paths": task.get("allowed_paths", []),
            "dependencies": task.get("dependencies", []),
        })
    return {
        "schema_version": "kanban-derived-view/1",
        "workflow_id": payload.get("workflow_id"),
        "source_taskset_sha256": source_hash,
        "generated_view": True,
        "do_not_edit": "Derived view; edit canonical TaskSet and rerender.",
        "cards": cards,
    }


def write_board_csv(payload: dict[str, Any], path: str | Path) -> None:
    source_hash = taskset_sha256(payload)
    fields = [
        "generated_view", "source_taskset_sha256", "do_not_edit", "workflow_id", "id", "title", "state",
        "card_type", "requirement_id", "purpose_id", "outcome_stage", "reporting_boundary", "objective",
        "workspace", "allowed_paths", "dependencies",
    ]
    with Path(path).open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for card in board_view(payload)["cards"]:
            row = {
                "generated_view": "true",
                "source_taskset_sha256": source_hash,
                "do_not_edit": "Derived view; edit canonical TaskSet and rerender.",
                "workflow_id": payload.get("workflow_id"),
                **card,
                "allowed_paths": " | ".join(str(x) for x in card.get("allowed_paths", [])),
                "dependencies": " | ".join(str(x) for x in card.get("dependencies", [])),
            }
            writer.writerow(row)


def validate_budget_policy(policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if policy.get("schema_version") != "workflow-budget-policy/1":
        errors.append("Budget policy schema_version must be 'workflow-budget-policy/1'.")
    if not isinstance(policy.get("policy_id"), str) or not str(policy.get("policy_id", "")).strip():
        errors.append("Budget policy requires a non-empty policy_id.")
    thresholds = policy.get("thresholds")
    if not isinstance(thresholds, dict):
        errors.append("Budget policy requires a thresholds object.")
    else:
        for key in THRESHOLD_METRIC_MAP:
            value = thresholds.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"Budget policy threshold {key!r} must be an integer >= 0.")
    gate = policy.get("evidence_gate")
    if not isinstance(gate, dict):
        errors.append("Budget policy requires an evidence_gate object.")
    else:
        minimum = gate.get("minimum_samples_per_value")
        delta = gate.get("minimum_failure_rate_delta")
        if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
            errors.append("Budget policy evidence_gate.minimum_samples_per_value must be an integer >= 1.")
        if not isinstance(delta, (int, float)) or isinstance(delta, bool) or not 0 <= float(delta) <= 1:
            errors.append("Budget policy evidence_gate.minimum_failure_rate_delta must be between 0 and 1.")
        if gate.get("direction") != "tighten-only":
            errors.append("Budget policy evidence_gate.direction must be 'tighten-only'.")
    return errors


def lint_taskset(payload: dict[str, Any], policy: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    active_policy = copy.deepcopy(DEFAULT_BUDGET_POLICY) if policy is None else policy
    policy_errors = validate_budget_policy(active_policy)
    if policy_errors:
        return [f"budget policy: {error}" for error in policy_errors]
    thresholds = active_policy["thresholds"]
    policy_id = active_policy["policy_id"]
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        return ["TaskSet must contain a non-empty tasks array."]

    ids = [t.get("id") for t in tasks]
    seen: set[str] = set()
    for task_id in ids:
        if not isinstance(task_id, str) or not task_id.strip():
            errors.append("Every task must have a non-empty id.")
        elif task_id in seen:
            errors.append(f"Duplicate task id: {task_id}")
        else:
            seen.add(task_id)

    by_id = {t.get("id"): t for t in tasks if isinstance(t.get("id"), str)}
    workflow_invariants, invariant_errors = _workflow_invariants(payload)
    errors.extend(invariant_errors)
    requirements, requirement_errors = _declared_source_items(payload, "REQUIREMENT")
    purposes, purpose_errors = _declared_source_items(payload, "PURPOSE")
    errors.extend(requirement_errors)
    errors.extend(purpose_errors)
    referenced_requirements: set[str] = set()
    referenced_purposes: set[str] = set()
    task_requirement: dict[str, str] = {}
    task_stage: dict[str, str] = {}
    artefact_owners: dict[str, list[tuple[str, str | None, str]]] = {}

    for task in tasks:
        task_id = task.get("id", "<missing-id>")
        ctype_values = _context_values(task, "CARD TYPE:")
        if len(ctype_values) != 1 or ctype_values[0].upper() not in CARD_TYPES:
            errors.append(f"{task_id}: exactly one CARD TYPE is required from {sorted(CARD_TYPES)}.")
        ctype = ctype_values[0].upper() if len(ctype_values) == 1 else None

        template_values = _context_values(task, "TASK TEMPLATE:")
        if len(template_values) != 1:
            errors.append(f"{task_id}: exactly one TASK TEMPLATE is required.")
        elif ctype and template_values[0].upper() != ctype:
            errors.append(f"{task_id}: TASK TEMPLATE {template_values[0]!r} must match CARD TYPE {ctype}.")

        profile_values = _context_values(task, "EVIDENCE PROFILE:")
        if len(profile_values) != 1:
            errors.append(f"{task_id}: exactly one EVIDENCE PROFILE is required.")
        elif ctype and profile_values[0].upper() != ctype:
            errors.append(f"{task_id}: EVIDENCE PROFILE {profile_values[0]!r} must match CARD TYPE {ctype}.")

        reporting_values = _context_values(task, "REPORTING BOUNDARY:")
        if len(reporting_values) != 1:
            errors.append(f"{task_id}: exactly one REPORTING BOUNDARY is required.")
        elif ctype:
            boundary = reporting_values[0].lower()
            allowed_boundaries = REPORTING_BOUNDARIES_BY_TYPE.get(ctype, set())
            if boundary not in allowed_boundaries:
                errors.append(
                    f"{task_id}: REPORTING BOUNDARY for {ctype} must be one of {sorted(allowed_boundaries)}, got {boundary!r}."
                )

        requirement_values = _context_values(task, "REQUIREMENT ID:")
        if len(requirement_values) != 1:
            errors.append(f"{task_id}: exactly one REQUIREMENT ID is required.")
        else:
            requirement_id = requirement_values[0]
            referenced_requirements.add(requirement_id)
            task_requirement[str(task_id)] = requirement_id
            if requirement_id not in requirements:
                errors.append(f"{task_id}: REQUIREMENT ID {requirement_id!r} is not declared in source_request.")

        purpose_values = _context_values(task, "PURPOSE ID:")
        if len(purpose_values) != 1:
            errors.append(f"{task_id}: exactly one PURPOSE ID is required.")
        else:
            purpose_id = purpose_values[0]
            referenced_purposes.add(purpose_id)
            if purpose_id not in purposes:
                errors.append(f"{task_id}: PURPOSE ID {purpose_id!r} is not declared in source_request.")

        provenance, provenance_errors = _provenance_records(task)
        errors.extend(f"{task_id}: {error}" for error in provenance_errors)
        if not provenance:
            errors.append(f"{task_id}: at least one valid PROVENANCE record is required.")

        stage_values = _context_values(task, "OUTCOME STAGE:")
        expected_stage = OUTCOME_STAGE_BY_TYPE.get(ctype) if ctype else None
        if len(stage_values) != 1:
            errors.append(f"{task_id}: exactly one OUTCOME STAGE is required.")
        else:
            stage = stage_values[0].upper()
            task_stage[str(task_id)] = stage
            if expected_stage and stage != expected_stage:
                errors.append(
                    f"{task_id}: OUTCOME STAGE for {ctype} must be {expected_stage}, got {stage}."
                )

        key_values = _context_values(task, "LIFECYCLE logical key:")
        version_values = _context_values(task, "LIFECYCLE contract version:")
        supersede_values = _context_values(task, "LIFECYCLE supersedes:")
        if len(key_values) != 1:
            errors.append(f"{task_id}: exactly one LIFECYCLE logical key is required.")
        if len(version_values) != 1:
            errors.append(f"{task_id}: exactly one LIFECYCLE contract version is required.")
        if len(supersede_values) != 1:
            errors.append(f"{task_id}: exactly one LIFECYCLE supersedes value is required.")

        version = contract_version(task)
        key = logical_key(task)
        if len(version_values) == 1 and version is None:
            errors.append(f"{task_id}: LIFECYCLE contract version must be an integer >= 1.")
        if key and version:
            expected_id = expected_task_id(key, version)
            if task_id != expected_id:
                errors.append(
                    f"{task_id}: deterministic identity mismatch; expected {expected_id} "
                    f"for logical key {key!r} version {version}."
                )

        if version == 1 and supersedes(task) not in {"none", "NONE"}:
            errors.append(f"{task_id}: contract version 1 must declare LIFECYCLE supersedes: none.")
        if version and version > 1 and supersedes(task) in {None, "none", "NONE", ""}:
            errors.append(f"{task_id}: successor contracts must declare the superseded task id.")

        repo_state_values = _context_values(task, "REPOSITORY STATE:")
        if len(repo_state_values) != 1 or repo_state_values[0].lower() not in REPOSITORY_STATES:
            errors.append(
                f"{task_id}: exactly one REPOSITORY STATE is required from {sorted(REPOSITORY_STATES)}."
            )
        elif repo_state_values[0].lower() == "pinned":
            required_repo = {
                "root": "REPOSITORY root:",
                "worktree": "REPOSITORY worktree:",
                "ref": "REPOSITORY ref:",
                "head": "REPOSITORY head:",
                "dirty": "REPOSITORY dirty:",
            }
            repo_values: dict[str, str | None] = {}
            for label, prefix in required_repo.items():
                values = _context_values(task, prefix)
                repo_values[label] = values[0] if len(values) == 1 else None
                if len(values) != 1 or not values[0].strip():
                    errors.append(f"{task_id}: repository pin requires exactly one non-empty {label} value.")
            head = repo_values.get("head")
            if head and not re.fullmatch(r"[0-9A-Fa-f]{7,64}", head):
                errors.append(f"{task_id}: repository pin head must be a 7-64 character hexadecimal Git object id.")
            dirty = repo_values.get("dirty")
            if dirty and dirty.lower() not in {"clean", "dirty"}:
                errors.append(f"{task_id}: repository pin dirty must be 'clean' or 'dirty'.")
        else:
            justifications = _context_values(task, "REPOSITORY JUSTIFICATION:")
            if len(justifications) != 1 or not justifications[0].strip():
                errors.append(
                    f"{task_id}: REPOSITORY STATE not-applicable requires exactly one REPOSITORY JUSTIFICATION."
                )

        lowering_values = _context_values(task, "LOWERING:")
        if len(lowering_values) != 1 or lowering_values[0].lower() not in LOWERING_MODES:
            errors.append(f"{task_id}: exactly one LOWERING mode is required from {sorted(LOWERING_MODES)}.")
            lowering = None
        else:
            lowering = lowering_values[0].lower()
        agentic_justifications = _context_values(task, "AGENTIC JUSTIFICATION:")
        if lowering == "bounded-agentic":
            if len(agentic_justifications) != 1 or not agentic_justifications[0].strip():
                errors.append(f"{task_id}: bounded-agentic lowering requires exactly one AGENTIC JUSTIFICATION.")
        elif lowering == "deterministic" and agentic_justifications:
            errors.append(f"{task_id}: deterministic lowering must not include AGENTIC JUSTIFICATION.")

        exception = has_complexity_exception(task)
        outputs = task.get("outputs", [])
        allowed_paths = task.get("allowed_paths", [])
        output_max = thresholds["primary_outputs_max"]
        path_max = thresholds["allowed_paths_max"]
        if isinstance(outputs, list) and len(outputs) > output_max and not exception:
            errors.append(
                f"{task_id}: primary deliverable budget exceeded under policy {policy_id}; "
                f"expected at most {output_max} output(s), got {len(outputs)}."
            )
        if isinstance(allowed_paths, list) and len(allowed_paths) > path_max and not exception:
            errors.append(
                f"{task_id}: write-path budget exceeded under policy {policy_id}; "
                f"expected at most {path_max} allowed_paths, got {len(allowed_paths)}."
            )

        artefacts, artefact_errors = _artefact_contracts(task)
        errors.extend(f"{task_id}: {error}" for error in artefact_errors)
        for artefact_path in artefacts:
            normalised = _normalise_path_value(artefact_path)
            artefact_owners.setdefault(normalised, []).append((str(task_id), logical_key(task), artefact_path))
        if isinstance(outputs, list):
            for output in outputs:
                if str(output) not in artefacts:
                    errors.append(f"{task_id}: output {output!r} is missing an ARTEFACT CONTRACT.")
            for artefact_path in artefacts:
                if artefact_path not in {str(x) for x in outputs}:
                    errors.append(
                        f"{task_id}: artefact contract path {artefact_path!r} is not declared in outputs."
                    )

        fingerprint = task.get("fingerprint", {}) or {}
        if not exception and fingerprint.get("reasoning") not in {None, "low"}:
            errors.append(f"{task_id}: reasoning budget exceeded; fingerprint.reasoning must be low.")
        if not exception and fingerprint.get("ambiguity") not in {None, "low"}:
            errors.append(f"{task_id}: ambiguity budget exceeded; fingerprint.ambiguity must be low.")
        if lowering == "deterministic" and fingerprint.get("determinism") != "high":
            errors.append(f"{task_id}: deterministic lowering requires fingerprint.determinism to be high.")

        prose = "\n".join(
            [str(task.get("objective", ""))]
            + [str(x) for x in task.get("scope", []) if isinstance(x, str)]
        ).lower()
        for phrase in AMBIGUOUS_PHRASES:
            if phrase in prose:
                errors.append(f"{task_id}: ambiguous phrase {phrase!r} must be resolved before release.")

        evidence_methods = _evidence_methods(task)
        if ctype in EVIDENCE_PROFILE_RULES:
            rule = EVIDENCE_PROFILE_RULES[ctype]
            missing_all = sorted(rule["all"] - evidence_methods)
            if missing_all:
                errors.append(
                    f"{task_id}: EVIDENCE PROFILE {ctype} requires evidence method(s) {missing_all}."
                )
            required_any = rule["any"]
            if required_any and not (evidence_methods & required_any):
                errors.append(
                    f"{task_id}: EVIDENCE PROFILE {ctype} requires at least one of {sorted(required_any)}."
                )

        command_evidence: list[dict[str, Any]] = []
        for acceptance in task.get("acceptance", []):
            if not isinstance(acceptance, dict):
                continue
            for evidence in acceptance.get("evidence_requirements", []):
                if isinstance(evidence, dict) and evidence.get("method") == "command_exit":
                    command_evidence.append(evidence)
        if command_evidence and not str(task.get("workspace", "")).strip():
            errors.append(f"{task_id}: exact command contracts require a non-empty workspace working directory.")
        for evidence in command_evidence:
            target = str(evidence.get("target", "")).strip()
            expected = str(evidence.get("expected", "")).strip()
            target_lower = target.lower()
            if not target or any(phrase in target_lower for phrase in VAGUE_COMMAND_PHRASES):
                errors.append(
                    f"{task_id}: exact command contract requires a copy-pasteable command target; got {target!r}."
                )
            expected_lower = expected.lower()
            if "exit" not in expected_lower or not (
                "zero" in expected_lower
                or re.search(r"\bexit\s*[:=]?\s*-?\d+\b", expected_lower)
                or re.search(r"\b-?\d+\s+exit\b", expected_lower)
            ):
                errors.append(
                    f"{task_id}: command_exit evidence must declare the expected exit result explicitly."
                )
        command_max = thresholds["command_contracts_max"]
        if len(command_evidence) > command_max and not exception:
            errors.append(
                f"{task_id}: command-contract budget exceeded under policy {policy_id}; "
                f"expected at most {command_max}, got {len(command_evidence)}."
            )
        if command_evidence and "shell" not in _required_capabilities(task):
            errors.append(f"{task_id}: command_exit evidence requires executor capability 'shell'.")

        constraints = [str(x) for x in task.get("constraints", []) if isinstance(x, str)]
        reporting_rules = [x for x in constraints if x.startswith("Reporting boundary:")]
        if len(reporting_rules) != 1:
            errors.append(f"{task_id}: exactly one Reporting boundary: constraint is required.")
        expected_inherited = {
            f"INHERITED INVARIANT {key}: {text}" for key, text in workflow_invariants.items()
        }
        actual_inherited = {x for x in constraints if x.startswith("INHERITED INVARIANT ")}
        for key, text in workflow_invariants.items():
            expected_line = f"INHERITED INVARIANT {key}: {text}"
            if expected_line not in actual_inherited:
                errors.append(f"{task_id}: workflow invariant {key} is not inherited verbatim by this card.")
        for line in sorted(actual_inherited - expected_inherited):
            errors.append(f"{task_id}: undeclared or altered workflow invariant constraint: {line!r}.")

        if ctype in MODIFYING_TYPES:
            if not allowed_paths:
                errors.append(f"{task_id}: modifying card requires an explicit allowed_paths write boundary.")
            if not any("Stop on surprise:" in str(x) for x in task.get("constraints", [])):
                errors.append(f"{task_id}: modifying card requires the standard Stop on surprise constraint.")

        for dep in task.get("dependencies", []):
            if dep not in by_id:
                errors.append(f"{task_id}: dependency {dep!r} does not exist in this TaskSet.")
            if dep == task_id:
                errors.append(f"{task_id}: task cannot depend on itself.")

    for requirement_id in sorted(set(requirements) - referenced_requirements):
        errors.append(f"Declared requirement {requirement_id!r} is not covered by any task REQUIREMENT ID.")
    for purpose_id in sorted(set(purposes) - referenced_purposes):
        errors.append(f"Declared purpose {purpose_id!r} is not referenced by any task PURPOSE ID.")

    for owners in artefact_owners.values():
        logical_keys = {key for _, key, _ in owners if key}
        if len(logical_keys) > 1:
            path = owners[0][2]
            detail = ", ".join(f"{task_id} ({key})" for task_id, key, _ in owners)
            errors.append(
                f"Artefact ownership conflict for {path!r}: different logical keys declare the same primary output: {detail}."
            )

    # Detect cycles with DFS.
    graph = {t.get("id"): list(t.get("dependencies", [])) for t in tasks if t.get("id")}
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for dep in graph.get(node, []):
            if dep in graph and dfs(dep):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    if any(dfs(node) for node in graph if node not in visited):
        errors.append("Dependency graph contains a cycle.")

    reach = _dependency_reachability(tasks)

    # Within one requirement, preserve the explicit executed -> verified -> accepted chain.
    by_requirement: dict[str, list[str]] = {}
    for task_id, requirement_id in task_requirement.items():
        by_requirement.setdefault(requirement_id, []).append(task_id)
    for requirement_id, task_ids in by_requirement.items():
        executed = [tid for tid in task_ids if task_stage.get(tid) == "EXECUTED"]
        verified = [tid for tid in task_ids if task_stage.get(tid) == "VERIFIED"]
        accepted = [tid for tid in task_ids if task_stage.get(tid) == "ACCEPTED"]
        if executed and verified:
            for tid in verified:
                if not any(exec_id in reach.get(tid, set()) for exec_id in executed):
                    errors.append(
                        f"{tid}: VERIFIED outcome for {requirement_id} must depend on prior EXECUTED work for the same requirement."
                    )
        if accepted:
            required_prior = verified if verified else executed
            for tid in accepted:
                if required_prior and not any(prev in reach.get(tid, set()) for prev in required_prior):
                    prior_name = "VERIFIED" if verified else "EXECUTED"
                    errors.append(
                        f"{tid}: ACCEPTED outcome for {requirement_id} must depend on prior {prior_name} work for the same requirement."
                    )

    # If a requirement has an ACCEPTED gate, downstream requirements must depend on that gate.
    accepted_gate_by_requirement = {
        requirement_id: {tid for tid in task_ids if task_stage.get(tid) == "ACCEPTED"}
        for requirement_id, task_ids in by_requirement.items()
    }
    for task in tasks:
        task_id = str(task.get("id", ""))
        own_requirement = task_requirement.get(task_id)
        for dep in task.get("dependencies", []):
            dep_requirement = task_requirement.get(str(dep))
            if not dep_requirement or dep_requirement == own_requirement:
                continue
            gates = accepted_gate_by_requirement.get(dep_requirement, set())
            if gates and dep not in gates:
                errors.append(
                    f"{task_id}: dependency {dep!r} targets an earlier stage of {dep_requirement}; depend on its ACCEPTED release gate instead."
                )

    # Treat tasks without a dependency path between them as potentially parallel.
    for i, left in enumerate(tasks):
        for right in tasks[i + 1 :]:
            left_id, right_id = left.get("id"), right.get("id")
            if not left_id or not right_id:
                continue
            ordered = right_id in reach.get(left_id, set()) or left_id in reach.get(right_id, set())
            if ordered:
                continue
            for lp in left.get("allowed_paths", []):
                for rp in right.get("allowed_paths", []):
                    if _path_overlap(str(lp), str(rp)):
                        errors.append(
                            f"{left_id} / {right_id}: parallel write collision on {lp!r} and {rp!r}; "
                            "add an ordering dependency or split ownership."
                        )
                        break
                else:
                    continue
                break

    return errors


def _normalised_contract(task: dict[str, Any]) -> dict[str, Any]:
    data = copy.deepcopy(task)
    for key in ("id", "state", "recorded_evidence"):
        data.pop(key, None)
    context = []
    for item in data.get("context", []):
        if isinstance(item, str) and (
            item.startswith("LIFECYCLE contract version:")
            or item.startswith("LIFECYCLE supersedes:")
        ):
            continue
        context.append(item)
    data["context"] = context
    return data


def reconcile(current: dict[str, Any], proposed: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    actions: list[str] = []

    current_errors = lint_taskset(current)
    proposed_errors = lint_taskset(proposed)
    if current_errors:
        errors.extend(f"current: {e}" for e in current_errors)
    if proposed_errors:
        errors.extend(f"proposed: {e}" for e in proposed_errors)
    if errors:
        return errors, actions

    def latest_by_key(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for task in payload["tasks"]:
            key = logical_key(task)
            ver = contract_version(task) or 0
            if key is None:
                continue
            if key not in result or ver > (contract_version(result[key]) or 0):
                result[key] = task
        return result

    old = latest_by_key(current)
    new = latest_by_key(proposed)

    for key in sorted(set(old) | set(new)):
        previous = old.get(key)
        candidate = new.get(key)
        if previous is None and candidate is not None:
            actions.append(f"NEW {candidate['id']} logical_key={key}")
            continue
        if previous is not None and candidate is None:
            actions.append(f"OBSOLETE {previous['id']} logical_key={key}")
            continue
        assert previous is not None and candidate is not None

        same_contract = _normalised_contract(previous) == _normalised_contract(candidate)
        if same_contract:
            if candidate["id"] != previous["id"] or contract_version(candidate) != contract_version(previous):
                errors.append(
                    f"{key}: unchanged contract must keep deterministic identity {previous['id']} "
                    f"and version {contract_version(previous)}."
                )
            else:
                actions.append(f"UNCHANGED {previous['id']} logical_key={key}")
            continue

        prev_state = str(previous.get("state", "held"))
        prev_version = contract_version(previous) or 1
        cand_version = contract_version(candidate) or 0
        if prev_state not in RELEASED_STATES:
            if candidate["id"] != previous["id"] or cand_version != prev_version:
                errors.append(
                    f"{key}: held contract may be updated in place; keep id {previous['id']} "
                    f"and version {prev_version}."
                )
            else:
                actions.append(f"UPDATE_HELD {previous['id']} logical_key={key}")
            continue

        # Released cards are immutable. Changed contracts must be successors.
        expected_version = prev_version + 1
        expected_id = expected_task_id(key, expected_version)
        if cand_version != expected_version or candidate.get("id") != expected_id or supersedes(candidate) != previous.get("id"):
            errors.append(
                f"{key}: released card {previous['id']} is immutable; changed contract must SUPERSEDE it "
                f"as {expected_id}, version {expected_version}, with LIFECYCLE supersedes: {previous['id']}."
            )
        else:
            actions.append(f"SUPERSEDE {previous['id']} -> {candidate['id']} logical_key={key}")

    return errors, actions


def check_capabilities(taskset: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    errors.extend(lint_taskset(taskset))
    profile_id = profile.get("profile_id")
    capabilities = profile.get("capabilities")
    if not isinstance(profile_id, str) or not profile_id.strip():
        errors.append("Executor capability profile requires a non-empty profile_id.")
    if not isinstance(capabilities, dict):
        errors.append("Executor capability profile requires a capabilities object.")
        return errors
    for name, value in capabilities.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(value, bool):
            errors.append("Executor capability profile entries must map non-empty capability names to booleans.")
    for task in taskset.get("tasks", []):
        task_id = task.get("id", "<missing-id>")
        for capability in sorted(_required_capabilities(task)):
            if capabilities.get(capability) is not True:
                errors.append(
                    f"{task_id}: required executor capability {capability!r} is unavailable in profile {profile_id!r}."
                )
    return errors



def _task_metrics(task: dict[str, Any]) -> dict[str, int]:
    command_count = 0
    for acceptance in task.get("acceptance", []):
        if not isinstance(acceptance, dict):
            continue
        for evidence in acceptance.get("evidence_requirements", []):
            if isinstance(evidence, dict) and evidence.get("method") == "command_exit":
                command_count += 1
    output_count = len(task.get("outputs", [])) if isinstance(task.get("outputs"), list) else 0
    path_count = len(task.get("allowed_paths", [])) if isinstance(task.get("allowed_paths"), list) else 0
    dep_count = len(task.get("dependencies", [])) if isinstance(task.get("dependencies"), list) else 0
    acceptance_count = len(task.get("acceptance", [])) if isinstance(task.get("acceptance"), list) else 0
    instruction_chars = len(json.dumps(_normalised_contract(task), sort_keys=True, ensure_ascii=False))
    complexity_score = (2 * output_count) + (2 * path_count) + command_count + dep_count + acceptance_count
    return {
        "output_count": output_count,
        "allowed_path_count": path_count,
        "dependency_count": dep_count,
        "acceptance_count": acceptance_count,
        "command_contract_count": command_count,
        "instruction_chars": instruction_chars,
        "complexity_score": complexity_score,
    }


def validate_telemetry_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != "workflow-execution-telemetry/1":
        errors.append("schema_version must be 'workflow-execution-telemetry/1'.")
    for key in ("execution_id", "recorded_at", "workflow_id", "task_id", "logical_key", "card_type", "executor_profile_id", "outcome_stage"):
        if not isinstance(record.get(key), str) or not str(record.get(key, "")).strip():
            errors.append(f"{key} must be a non-empty string.")
    digest = record.get("taskset_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        errors.append("taskset_sha256 must be a lowercase 64-character SHA-256 hex digest.")
    version = record.get("contract_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        errors.append("contract_version must be an integer >= 1.")
    if record.get("card_type") not in CARD_TYPES:
        errors.append(f"card_type must be one of {sorted(CARD_TYPES)}.")
    result = record.get("result")
    failure_class = record.get("failure_class")
    if result not in TELEMETRY_RESULTS:
        errors.append(f"result must be one of {sorted(TELEMETRY_RESULTS)}.")
    elif result == "FAILURE":
        if failure_class not in FAILURE_CLASSES:
            errors.append(f"FAILURE telemetry requires failure_class from {sorted(FAILURE_CLASSES)}.")
    elif failure_class is not None:
        errors.append("SUCCESS telemetry must set failure_class to null.")
    duration = record.get("duration_ms")
    if not isinstance(duration, int) or isinstance(duration, bool) or duration < 0:
        errors.append("duration_ms must be an integer >= 0.")
    attempt = record.get("attempt")
    if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
        errors.append("attempt must be an integer >= 1.")
    metrics = record.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("metrics must be an object.")
    else:
        for key in TELEMETRY_METRICS:
            value = metrics.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"{key} must be an integer >= 0.")
    return errors


def _telemetry_record_from_task(
    payload: dict[str, Any], task: dict[str, Any], *, execution_id: str, recorded_at: str,
    executor_profile_id: str, result: str, failure_class: str | None, duration_ms: int, attempt: int,
) -> dict[str, Any]:
    return {
        "schema_version": "workflow-execution-telemetry/1",
        "execution_id": execution_id,
        "recorded_at": recorded_at,
        "workflow_id": payload.get("workflow_id"),
        "taskset_sha256": taskset_sha256(payload),
        "task_id": task.get("id"),
        "logical_key": logical_key(task),
        "contract_version": contract_version(task),
        "card_type": card_type(task),
        "executor_profile_id": executor_profile_id,
        "result": result,
        "failure_class": failure_class,
        "duration_ms": duration_ms,
        "attempt": attempt,
        "outcome_stage": _single_context(task, "OUTCOME STAGE:"),
        "metrics": _task_metrics(task),
    }


def analyse_telemetry(records: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any] | None]:
    errors: list[str] = []
    seen: set[str] = set()
    for record in records:
        rec_errors = validate_telemetry_record(record)
        rid = str(record.get("execution_id", "<missing>"))
        errors.extend(f"{rid}: {error}" for error in rec_errors)
        if rid in seen:
            errors.append(f"duplicate execution_id {rid!r}.")
        seen.add(rid)
    if errors:
        return errors, None
    ordered = sorted(records, key=lambda r: r["execution_id"])
    failures = [r for r in ordered if r["result"] == "FAILURE"]
    by_card_type: dict[str, dict[str, Any]] = {}
    for ctype in sorted({r["card_type"] for r in ordered}):
        subset = [r for r in ordered if r["card_type"] == ctype]
        count_fail = sum(r["result"] == "FAILURE" for r in subset)
        by_card_type[ctype] = {
            "records": len(subset), "failures": count_fail,
            "failure_rate": round(count_fail / len(subset), 6),
        }
    by_failure_class = {name: sum(r.get("failure_class") == name for r in failures) for name in sorted(FAILURE_CLASSES)}
    by_failure_class = {k: v for k, v in by_failure_class.items() if v}
    metric_report: dict[str, list[dict[str, Any]]] = {}
    for metric in TELEMETRY_METRICS:
        rows: list[dict[str, Any]] = []
        for value in sorted({r["metrics"][metric] for r in ordered}):
            subset = [r for r in ordered if r["metrics"][metric] == value]
            count_fail = sum(r["result"] == "FAILURE" for r in subset)
            instruction_failures = sum(r.get("failure_class") in {"INSTRUCTION_AMBIGUITY", "CONTRACT_MISMATCH"} for r in subset)
            rows.append({
                "value": value,
                "records": len(subset),
                "failures": count_fail,
                "failure_rate": round(count_fail / len(subset), 6),
                "instruction_failures": instruction_failures,
                "instruction_failure_rate": round(instruction_failures / len(subset), 6),
            })
        metric_report[metric] = rows
    report = {
        "schema_version": "workflow-telemetry-analysis/1",
        "record_count": len(ordered),
        "success_count": len(ordered) - len(failures),
        "failure_count": len(failures),
        "failure_rate": round(len(failures) / len(ordered), 6) if ordered else 0.0,
        "by_card_type": by_card_type,
        "by_failure_class": by_failure_class,
        "metrics": metric_report,
        "execution_ids": [r["execution_id"] for r in ordered],
        "interpretation": "association-only; correlation is not causation",
    }
    return [], report


def recommend_budgets(analysis: dict[str, Any], policy: dict[str, Any]) -> tuple[list[str], dict[str, Any] | None]:
    errors = validate_budget_policy(policy)
    if analysis.get("schema_version") != "workflow-telemetry-analysis/1":
        errors.append("Telemetry analysis schema_version must be 'workflow-telemetry-analysis/1'.")
    metrics = analysis.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("Telemetry analysis requires a metrics object.")
    if errors:
        return errors, None
    minimum = policy["evidence_gate"]["minimum_samples_per_value"]
    delta = float(policy["evidence_gate"]["minimum_failure_rate_delta"])
    changes: list[dict[str, Any]] = []
    sufficient_pairs = 0
    for threshold_name, metric_name in THRESHOLD_METRIC_MAP.items():
        current = policy["thresholds"][threshold_name]
        if current <= 0:
            continue
        rows = {row.get("value"): row for row in metrics.get(metric_name, []) if isinstance(row, dict)}
        lower = rows.get(current - 1)
        higher = rows.get(current)
        if not lower or not higher:
            continue
        if lower.get("records", 0) < minimum or higher.get("records", 0) < minimum:
            continue
        sufficient_pairs += 1
        lower_rate = float(lower.get("failure_rate", 0.0))
        higher_rate = float(higher.get("failure_rate", 0.0))
        if higher_rate - lower_rate >= delta:
            changes.append({
                "threshold": threshold_name,
                "metric": metric_name,
                "current": current,
                "proposed": current - 1,
                "reason": "higher contract metric is associated with materially higher observed failure rate",
                "evidence": {
                    "minimum_samples_per_value": minimum,
                    "lower_records": lower["records"],
                    "higher_records": higher["records"],
                    "lower_failure_rate": lower_rate,
                    "higher_failure_rate": higher_rate,
                    "observed_delta": round(higher_rate - lower_rate, 6),
                    "required_delta": delta,
                },
            })
    if changes:
        status = "PROPOSED_CHANGES"
    elif sufficient_pairs:
        status = "RETAIN_POLICY"
    else:
        status = "INSUFFICIENT_EVIDENCE"
    proposal = {
        "schema_version": "workflow-budget-proposal/1",
        "status": status,
        "auto_apply": False,
        "direction": "tighten-only",
        "source_policy_id": policy["policy_id"],
        "source_policy_sha256": taskset_sha256(policy),
        "source_analysis_sha256": taskset_sha256(analysis),
        "changes": changes,
        "evidence_gate": copy.deepcopy(policy["evidence_gate"]),
        "note": "Review explicitly; never auto-apply telemetry-derived policy changes.",
    }
    return [], proposal

def print_errors(errors: list[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}")


def cmd_lint(args: argparse.Namespace) -> int:
    payload = load_json(args.taskset)
    policy = load_json(args.policy) if getattr(args, "policy", None) else None
    errors = lint_taskset(payload, policy)
    policy_id = (policy or DEFAULT_BUDGET_POLICY)["policy_id"] if not errors or (policy and isinstance(policy, dict) and policy.get("policy_id")) else DEFAULT_BUDGET_POLICY["policy_id"]
    if errors:
        print_errors(errors)
        print(f"FAIL: {len(errors)} contract error(s) under budget policy {policy_id}.")
        return 1
    print(f"PASS: {len(payload['tasks'])} task(s) satisfy workflow-to-kanban portable contract checks under budget policy {policy_id}.")
    return 0


def cmd_reconcile(args: argparse.Namespace) -> int:
    current = load_json(args.current)
    proposed = load_json(args.proposed)
    errors, actions = reconcile(current, proposed)
    for action in actions:
        print(action)
    if errors:
        print_errors(errors)
        print(f"FAIL: reconciliation rejected with {len(errors)} error(s).")
        return 1
    print(f"PASS: reconciliation produced {len(actions)} action(s).")
    return 0


def cmd_lint_failure(args: argparse.Namespace) -> int:
    payload = load_json(args.failure_record)
    errors: list[str] = []
    if payload.get("failure_class") not in FAILURE_CLASSES:
        errors.append(
            f"failure_class must be one of {sorted(FAILURE_CLASSES)}; got {payload.get('failure_class')!r}."
        )
    for key in ("task_id", "summary", "evidence"):
        if key not in payload:
            errors.append(f"failure record is missing required field {key!r}.")
    if errors:
        print_errors(errors)
        print(f"FAIL: {len(errors)} failure-record error(s).")
        return 1
    print(f"PASS: failure record uses recognised class {payload['failure_class']}.")
    return 0


def cmd_id(args: argparse.Namespace) -> int:
    print(expected_task_id(args.logical_key, args.version))
    return 0


def cmd_check_capabilities(args: argparse.Namespace) -> int:
    taskset = load_json(args.taskset)
    profile = load_json(args.profile)
    errors = check_capabilities(taskset, profile)
    if errors:
        print_errors(errors)
        print(f"FAIL: capability gate rejected with {len(errors)} error(s).")
        return 1
    print(
        f"PASS: executor profile {profile['profile_id']} satisfies all required capabilities "
        f"for {len(taskset['tasks'])} task(s)."
    )
    return 0



def cmd_record_telemetry(args: argparse.Namespace) -> int:
    out = Path(args.output)
    if out.exists():
        print("ERROR: execution telemetry is immutable; output file already exists.")
        return 1
    payload = load_json(args.taskset)
    errors = lint_taskset(payload)
    if errors:
        print_errors(errors)
        print(f"FAIL: telemetry source TaskSet has {len(errors)} contract error(s).")
        return 1
    task = next((t for t in payload["tasks"] if t.get("id") == args.task_id), None)
    if task is None:
        print(f"ERROR: task_id {args.task_id!r} does not exist in TaskSet.")
        return 1
    failure_class = args.failure_class
    if args.result == "FAILURE" and failure_class not in FAILURE_CLASSES:
        print(f"ERROR: FAILURE telemetry requires failure_class from {sorted(FAILURE_CLASSES)}.")
        return 1
    if args.result == "SUCCESS" and failure_class is not None:
        print("ERROR: SUCCESS telemetry must not include failure_class.")
        return 1
    record = _telemetry_record_from_task(
        payload, task, execution_id=args.execution_id, recorded_at=args.recorded_at,
        executor_profile_id=args.executor_profile_id, result=args.result,
        failure_class=failure_class, duration_ms=args.duration_ms, attempt=args.attempt,
    )
    rec_errors = validate_telemetry_record(record)
    if rec_errors:
        print_errors(rec_errors)
        print(f"FAIL: telemetry record has {len(rec_errors)} error(s).")
        return 1
    _write_json(out, record)
    print(f"PASS: immutable execution telemetry written to {out}.")
    return 0


def cmd_lint_telemetry(args: argparse.Namespace) -> int:
    record = load_json(args.record)
    errors = validate_telemetry_record(record)
    if errors:
        print_errors(errors)
        print(f"FAIL: telemetry record has {len(errors)} error(s).")
        return 1
    print(f"PASS: execution telemetry {record['execution_id']} is structurally valid.")
    return 0


def cmd_analyse_telemetry(args: argparse.Namespace) -> int:
    records = [load_json(path) for path in args.records]
    errors, report = analyse_telemetry(records)
    if errors:
        print_errors(errors)
        print(f"FAIL: telemetry analysis rejected with {len(errors)} error(s).")
        return 1
    assert report is not None
    _write_json(args.output, report)
    print(f"PASS: analysed {report['record_count']} immutable execution record(s) into {args.output}.")
    return 0


def cmd_recommend_budgets(args: argparse.Namespace) -> int:
    analysis = load_json(args.analysis)
    policy = load_json(args.policy)
    errors, proposal = recommend_budgets(analysis, policy)
    if errors:
        print_errors(errors)
        print(f"FAIL: budget recommendation rejected with {len(errors)} error(s).")
        return 1
    assert proposal is not None
    _write_json(args.output, proposal)
    print(f"PASS: budget proposal status={proposal['status']} written to {args.output}; never auto-applied.")
    return 0

def _structured_plan(current: dict[str, Any], proposed: dict[str, Any]) -> dict[str, Any]:
    errors, actions = reconcile_details(current, proposed)
    return {
        "schema_version": "workflow-to-kanban-plan/1",
        "workflow_id": proposed.get("workflow_id"),
        "current_taskset_sha256": taskset_sha256(current),
        "proposed_taskset_sha256": taskset_sha256(proposed),
        "valid": not errors,
        "actions": actions,
        "errors": errors,
        "manifest_preview": workflow_manifest(proposed) if not errors else None,
    }


def cmd_dry_run(args: argparse.Namespace) -> int:
    current = load_json(args.current)
    proposed = load_json(args.proposed)
    errors, actions = reconcile(current, proposed)
    for action in actions:
        print(action)
    if errors:
        print_errors(errors)
        print(f"FAIL: dry-run rejected with {len(errors)} error(s). NO FILES WRITTEN.")
        return 1
    print(f"PASS: dry-run produced {len(actions)} reconciliation action(s). NO FILES WRITTEN.")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    current = load_json(args.current)
    proposed = load_json(args.proposed)
    report = _structured_plan(current, proposed)
    _write_json(args.output, report)
    if not report["valid"]:
        print_errors(report["errors"])
        print(f"FAIL: plan contains {len(report['errors'])} error(s); wrote diagnostic plan only.")
        return 1
    print(f"PASS: plan wrote {len(report['actions'])} explainable action(s) to {args.output}.")
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    payload = load_json(args.taskset)
    errors = lint_taskset(payload)
    if errors:
        print_errors(errors)
        print(f"FAIL: manifest generation rejected with {len(errors)} error(s).")
        return 1
    _write_json(args.output, workflow_manifest(payload))
    print(f"PASS: workflow manifest written to {args.output}.")
    return 0


def cmd_render_board(args: argparse.Namespace) -> int:
    payload = load_json(args.taskset)
    errors = lint_taskset(payload)
    if errors:
        print_errors(errors)
        print(f"FAIL: board rendering rejected with {len(errors)} error(s).")
        return 1
    _write_json(args.json, board_view(payload))
    write_board_csv(payload, args.csv)
    print(f"PASS: generated view written to {args.json} and {args.csv}; canonical TaskSet remains authoritative.")
    return 0


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def cmd_apply(args: argparse.Namespace) -> int:
    current_path = _resolved(args.current)
    proposed_path = _resolved(args.proposed)
    outputs = [_resolved(args.canonical_out), _resolved(args.manifest_out), _resolved(args.board_json_out), _resolved(args.csv_out)]
    if any(path in {current_path, proposed_path} for path in outputs):
        print("ERROR: apply refuses to overwrite reconciliation input files; write a new canonical successor and derived views.")
        return 1
    if len(set(outputs)) != len(outputs):
        print("ERROR: apply output paths must be distinct.")
        return 1
    current = load_json(current_path)
    proposed = load_json(proposed_path)
    errors, details = reconcile_details(current, proposed)
    if errors:
        print_errors(errors)
        print(f"FAIL: APPLY rejected with {len(errors)} reconciliation error(s).")
        return 1
    _write_json(args.canonical_out, proposed)
    _write_json(args.manifest_out, workflow_manifest(proposed))
    _write_json(args.board_json_out, board_view(proposed))
    write_board_csv(proposed, args.csv_out)
    print(
        f"PASS: APPLY wrote canonical successor plus regenerated derived views; "
        f"{len(details)} reconciliation action(s) validated."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    lint = sub.add_parser("lint", help="Lint one TaskSet for low-reasoning/lifecycle contract rules.")
    lint.add_argument("taskset")
    lint.add_argument("--policy", help="Optional workflow-budget-policy/1 JSON; defaults to built-in conservative policy.")
    lint.set_defaults(func=cmd_lint)

    rec = sub.add_parser("reconcile", help="Compare current and proposed TaskSets without rewriting released cards.")
    rec.add_argument("current")
    rec.add_argument("proposed")
    rec.set_defaults(func=cmd_reconcile)

    failure = sub.add_parser("lint-failure", help="Validate a structured failure record against the supported taxonomy.")
    failure.add_argument("failure_record")
    failure.set_defaults(func=cmd_lint_failure)

    identity = sub.add_parser("id", help="Derive a deterministic task id from logical key and contract version.")
    identity.add_argument("logical_key")
    identity.add_argument("version", type=int)
    identity.set_defaults(func=cmd_id)

    capability = sub.add_parser(
        "check-capabilities",
        help="Fail closed when an executor profile lacks a required task capability.",
    )
    capability.add_argument("taskset")
    capability.add_argument("profile")
    capability.set_defaults(func=cmd_check_capabilities)

    record = sub.add_parser("record-telemetry", help="Create one immutable execution telemetry record from canonical TaskSet data.")
    record.add_argument("taskset")
    record.add_argument("task_id")
    record.add_argument("--execution-id", required=True)
    record.add_argument("--recorded-at", required=True)
    record.add_argument("--executor-profile-id", required=True)
    record.add_argument("--result", choices=sorted(TELEMETRY_RESULTS), required=True)
    record.add_argument("--failure-class")
    record.add_argument("--duration-ms", type=int, required=True)
    record.add_argument("--attempt", type=int, required=True)
    record.add_argument("--output", required=True)
    record.set_defaults(func=cmd_record_telemetry)

    lint_telemetry = sub.add_parser("lint-telemetry", help="Validate one workflow-execution-telemetry/1 record.")
    lint_telemetry.add_argument("record")
    lint_telemetry.set_defaults(func=cmd_lint_telemetry)

    analyse = sub.add_parser("analyse-telemetry", help="Correlate failure patterns across immutable telemetry records.")
    analyse.add_argument("records", nargs="+")
    analyse.add_argument("--output", required=True)
    analyse.set_defaults(func=cmd_analyse_telemetry)

    recommend = sub.add_parser("recommend-budgets", help="Generate a non-applied evidence-gated budget policy proposal.")
    recommend.add_argument("analysis")
    recommend.add_argument("policy")
    recommend.add_argument("--output", required=True)
    recommend.set_defaults(func=cmd_recommend_budgets)

    dry_run = sub.add_parser("dry-run", help="Validate and reconcile without writing any files.")
    dry_run.add_argument("current")
    dry_run.add_argument("proposed")
    dry_run.set_defaults(func=cmd_dry_run)

    plan = sub.add_parser("plan", help="Write a structured, explainable reconciliation plan without applying it.")
    plan.add_argument("current")
    plan.add_argument("proposed")
    plan.add_argument("--output", required=True)
    plan.set_defaults(func=cmd_plan)

    manifest = sub.add_parser("manifest", help="Generate a deterministic workflow manifest from canonical TaskSet JSON.")
    manifest.add_argument("taskset")
    manifest.add_argument("--output", required=True)
    manifest.set_defaults(func=cmd_manifest)

    render = sub.add_parser("render-board", help="Render non-authoritative JSON/CSV board views from canonical TaskSet JSON.")
    render.add_argument("taskset")
    render.add_argument("--json", required=True)
    render.add_argument("--csv", required=True)
    render.set_defaults(func=cmd_render_board)

    apply = sub.add_parser("apply", help="Apply a reconciled proposal to a new canonical output and regenerate derived views.")
    apply.add_argument("current")
    apply.add_argument("proposed")
    apply.add_argument("--canonical-out", required=True)
    apply.add_argument("--manifest-out", required=True)
    apply.add_argument("--board-json-out", required=True)
    apply.add_argument("--csv-out", required=True)
    apply.set_defaults(func=cmd_apply)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
