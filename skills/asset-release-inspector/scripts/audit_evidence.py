#!/usr/bin/env python3
"""Offline evidence-record integrity audit. Never makes a release decision."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def fields(value, expected, label):
    require(isinstance(value, dict), f"{label}: must be an object")
    require(set(value) == set(expected), f"{label}: missing or unexpected fields: {sorted(set(value) ^ set(expected))}")


def string(value, label):
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= 4096,
            f"{label}: must be a nonempty string of at most 4096 characters")
    return value


def digest(value, label):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
            f"{label}: expected a lowercase SHA-256")
    return value


def unique_strings(value, label, nonempty=False):
    require(isinstance(value, list), f"{label}: must be an array")
    require(not nonempty or bool(value), f"{label}: cannot be empty")
    for item in value:
        string(item, label)
    require(len(value) == len(set(value)), f"{label}: duplicate values")
    return value


def file_hash(root, relative, label):
    string(relative, label)
    path = PurePosixPath(relative)
    require(not path.is_absolute() and ".." not in path.parts and "\\" not in relative
            and ":" not in relative and "\x00" not in relative and relative not in ("", "."),
            f"{label}: unsafe path")
    actual = root
    for part in path.parts:
        actual = actual / part
        require(not actual.is_symlink(), f"{label}: symlink paths are forbidden")
    require(actual.is_file(), f"{label}: not a regular file: {relative}")
    require(actual.resolve().is_relative_to(root), f"{label}: unsafe path outside root")
    require(stat.S_ISREG(actual.stat().st_mode), f"{label}: not a regular file")
    checksum = hashlib.sha256()
    with actual.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def audit(record, root, scope_id, source_revision, required_gates):
    """Return an integrity report; raises Invalid on the first invalid contract."""
    fields(record, ("schema_version", "scope", "artifacts", "required_gates", "gates"), "record")
    require(type(record["schema_version"]) is int and record["schema_version"] == 1,
            "schema_version: expected integer 1")
    fields(record["scope"], ("id", "source_revision"), "scope")
    string(scope_id, "current scope ID")
    string(source_revision, "current source revision")
    require(string(record["scope"]["id"], "scope.id") == scope_id, "scope does not match current scope ID")
    require(string(record["scope"]["source_revision"], "scope.source_revision") == source_revision,
            "scope does not match current source revision")
    expected = set(unique_strings(required_gates, "external required gates", nonempty=True))
    declared = set(unique_strings(record["required_gates"], "required_gates", nonempty=True))
    require(expected <= declared, f"record omits externally required gates: {sorted(expected - declared)}")
    require(isinstance(record["artifacts"], list) and bool(record["artifacts"]), "artifacts: nonempty array required")
    artifacts, seen_paths = {}, set()
    for artifact in record["artifacts"]:
        fields(artifact, ("id", "path", "sha256"), "artifact")
        identifier = string(artifact["id"], "artifact.id")
        require(identifier not in artifacts, f"duplicate artifact ID: {identifier}")
        path = string(artifact["path"], "artifact.path")
        normalized = str(PurePosixPath(path))
        require(normalized not in seen_paths, f"duplicate artifact path: {path}")
        seen_paths.add(normalized)
        checksum = digest(artifact["sha256"], "artifact.sha256")
        require(file_hash(root, path, f"artifact {identifier}") == checksum, f"artifact {identifier}: hash mismatch")
        artifacts[identifier] = checksum
    require(isinstance(record["gates"], list), "gates: array required")
    gates, counts, unresolved, na = set(), Counter(), [], []
    for gate in record["gates"]:
        fields(gate, ("id", "result", "rationale", "artifact_ids", "evidence"), "gate")
        identifier = string(gate["id"], "gate.id")
        require(identifier not in gates, f"duplicate gate ID: {identifier}")
        gates.add(identifier)
        result = string(gate["result"], "gate.result")
        require(result in ("pass", "fail", "blocked", "not_applicable"), f"gate {identifier}: unknown result")
        string(gate["rationale"], f"gate {identifier} rationale")
        targets = unique_strings(gate["artifact_ids"], f"gate {identifier} artifact_ids")
        require(set(targets) <= artifacts.keys(), f"gate {identifier}: unknown artifact ID")
        evidence = gate["evidence"]
        require(isinstance(evidence, list), f"gate {identifier}: evidence must be an array")
        if result in ("pass", "fail"):
            require(bool(targets), f"gate {identifier}: {result} requires target artifacts")
            require(bool(evidence), f"gate {identifier}: {result} requires evidence")
        evidence_paths = set()
        for item in evidence:
            fields(item, ("path", "sha256", "scope_id", "source_revision", "artifact_sha256"), "evidence")
            require(item["scope_id"] == scope_id, f"gate {identifier}: evidence scope mismatch")
            require(item["source_revision"] == source_revision, f"gate {identifier}: evidence source revision mismatch")
            require(item["artifact_sha256"] == {target: artifacts[target] for target in targets},
                    f"gate {identifier}: evidence artifact bindings mismatch")
            path = string(item["path"], "evidence.path")
            normalized = str(PurePosixPath(path))
            require(normalized not in evidence_paths, f"gate {identifier}: duplicate evidence path")
            evidence_paths.add(normalized)
            checksum = digest(item["sha256"], "evidence.sha256")
            require(file_hash(root, path, "evidence") == checksum, f"gate {identifier}: evidence hash mismatch")
        counts[result] += 1
        if result in ("fail", "blocked"):
            unresolved.append(identifier)
        if result == "not_applicable":
            na.append(identifier)
    require(declared <= gates, f"missing required gate IDs: {sorted(declared - gates)}")
    return {
        "integrity": "verified", "release_decision": "not_evaluated",
        "scope": record["scope"], "artifact_count": len(artifacts), "gate_count": len(gates),
        "declared_results": {key: counts[key] for key in ("pass", "fail", "blocked", "not_applicable")},
        "unresolved_gate_ids": sorted(unresolved), "not_applicable_gate_ids": sorted(na),
        "errors": [],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--scope-id", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--required-gate", dest="required_gates", action="append", required=True)
    args = parser.parse_args(argv)
    try:
        require(args.root.is_dir(), "release root must be a directory")
        require(not args.root.is_symlink(), "release root may not be a symlink")
        require(args.record.is_file() and not args.record.is_symlink(), "record must be a regular non-symlink file")
        require(args.record.stat().st_size <= 2 * 1024 * 1024, "record exceeds 2 MiB limit")
        record = json.loads(args.record.read_text(encoding="utf-8"), object_pairs_hook=no_duplicate_keys)
        report = audit(record, args.root.resolve(), args.scope_id, args.source_revision, args.required_gates)
        code = 0
    except (Invalid, OSError, ValueError, RecursionError) as error:
        report = {"integrity": "invalid", "release_decision": "not_evaluated", "errors": [str(error)]}
        code = 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
