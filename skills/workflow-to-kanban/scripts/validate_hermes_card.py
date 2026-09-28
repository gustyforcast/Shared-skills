#!/usr/bin/env python3
"""Fail-closed static checks for Hermes successor review/worker card text."""

import argparse
import json
import re
from pathlib import Path

LIFECYCLE = (
    "kanban_complete",
    "kanban_block",
    "kanban_request_review",
    "kanban_request_changes",
)

CONTRADICTION_PATTERNS = (
    r"do\s+not\s+call.{0,60}(?:kanban|lifecycle)",
    r"never\s+call.{0,60}(?:kanban|lifecycle)",
    r"without.{0,40}(?:kanban|lifecycle)\s+call",
)

WRITE_WORDS = r"(?:write|create|save|output|emit)"
WINDOWS_PATH = r"[A-Za-z]:\\\S+"
CONTAINER_PATH = r"/(?:workspace|evidence|reports)(?:/\S+)?"


def _lifecycle_mentions(text):
    found = []
    lower = text.lower()
    for name in LIFECYCLE:
        found.extend([name] * lower.count(name))
    return found


def _write_target_issues(text):
    issues = []
    for line in text.splitlines():
        if not re.search(WRITE_WORDS, line, flags=re.IGNORECASE):
            continue
        lower_line = line.lower()
        negated_write = re.search(r"(?:do\s+not|don't|never).{0,24}\bwrite\b", lower_line)
        if re.search(WINDOWS_PATH, line) and not negated_write:
            issues.append("windows_sandbox_write_path")
        container_paths = re.findall(CONTAINER_PATH, line)
        if len(container_paths) > 1:
            issues.append("multiple_model_authored_artifacts")
    return issues


def validate_text(text):
    issues = []
    lower = text.lower()
    mentions = _lifecycle_mentions(text)

    if not re.search(
        r"\b(?:run|execute)\b[\s\S]{0,160}?(?:\.py|\.ps1|\.mjs|\.js)\b",
        lower,
    ):
        issues.append("missing_deterministic_script")

    # code-reviewer live guard compatibility:
    # Python reviewer scripts must be /evidence/<card>/run_review_checks.py.
    reviewer_python = re.findall(r"\bpython(?:3)?\s+(/evidence/\S+?\.py)\b", text, flags=re.IGNORECASE)
    if reviewer_python:
        if len(reviewer_python) != 1 or re.fullmatch(
            r"/evidence/[A-Za-z0-9._-]+/run_review_checks\.py",
            reviewer_python[0],
        ) is None:
            issues.append("reviewer_script_guard_mismatch")
        if "first substantive tool call" not in lower:
            issues.append("missing_first_substantive_tool_gate")
        no_discovery = (
            re.search(r"do\s+not\s+call", lower) is not None
            and all(name in lower for name in ("search_files", "read_file", "list_directory", "pwd", "git"))
            and ("before that runner" in lower or "before the runner" in lower)
        )
        if not no_discovery:
            issues.append("missing_no_discovery_gate")

    model_verdict = re.search(
        r"(?ms)^\s*(?:the\s+model\s+)?writes?\s+exactly\s+one[^\n]*verdict"
        r"[^\n]*(?:\n\s*)?/reports/\S+",
        lower,
    )
    script_verdict = re.search(
        r"(?m)^\s*[^\n]*(?:script|runner)(?:\s+(?:must|will|should))?\s+writes?"
        r"[^\n]*verdict",
        lower,
    )
    if not model_verdict:
        issues.append("missing_single_verdict_artifact")
    elif reviewer_python:
        verdict_path_match = re.search(
            r"(?ms)^\s*(?:the\s+model\s+)?writes?\s+exactly\s+one[^\n]*verdict"
            r"[^\n]*(?:\n\s*)?(/reports/\S+)",
            text,
            flags=re.IGNORECASE,
        )
        verdict_path = verdict_path_match.group(1).rstrip(".,;:") if verdict_path_match else ""
        if re.fullmatch(r"/reports/[A-Za-z0-9._-]+\.verdict\.json", verdict_path) is None:
            issues.append("reviewer_verdict_guard_mismatch")
    if script_verdict:
        issues.append("verdict_not_model_owned")
    if not re.search(r"exactly\s+one[^\n]*lifecycle\s+call", lower):
        issues.append("missing_exactly_one_lifecycle_instruction")

    scripted_lifecycle = "lifecycle_action" in lower
    if not mentions and not scripted_lifecycle:
        issues.append("missing_terminal_lifecycle")
    elif len(set(mentions)) > 1:
        issues.append("multiple_terminal_lifecycle_actions")

    if any(re.search(p, lower) for p in CONTRADICTION_PATTERNS):
        issues.append("contradictory_lifecycle_instruction")

    issues.extend(_write_target_issues(text))
    return sorted(set(issues))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("card")
    args = parser.parse_args()
    text = Path(args.card).read_text(encoding="utf-8")
    issues = validate_text(text)
    print(json.dumps({"valid": not issues, "issues": issues}, indent=2))
    raise SystemExit(1 if issues else 0)


if __name__ == "__main__":
    main()
