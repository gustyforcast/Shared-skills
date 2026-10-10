# Shared evidence contract, version 1

Use this optional offline helper for asset and general artefact reviews. It is an integrity check, not a specialist validator. The current approved scope, source revision, required gates, and expected deliverables must be established outside the candidate evidence record. A worker's declaration is never its own acceptance authority.

```sh
python3 skills/asset-release-inspector/scripts/audit_evidence.py <record.json> \
  --root <release-root> --scope-id <current-scope-id> \
  --source-revision <current-source-revision> \
  --required-gate content --required-gate visual
```

Python 3.10+ and the standard library are the only runtime dependencies. The helper reads local files and emits JSON to stdout. It performs no writes, networking, subprocess calls, or evaluation of file contents. Missing Python/filesystem capability is `blocked`, never an inferred pass.

## Input

All keys below are required. Extra keys, duplicate JSON object keys/IDs, duplicate artifact references, and unknown results are rejected. Paths must be relative to `--root`, must remain within it, and may not cross symlinks. Use a separate explicit release root containing only the files approved for this review.

```json
{
  "schema_version": 1,
  "scope": {"id": "example-release", "source_revision": "approved-plan-r4"},
  "artifacts": [{"id": "slides", "path": "final/slides.pptx", "sha256": "64 lowercase hexadecimal characters"}],
  "required_gates": ["content", "visual"],
  "gates": [{
    "id": "content",
    "result": "pass",
    "rationale": "Describe the actual check and its limits.",
    "artifact_ids": ["slides"],
    "evidence": [{
      "path": "evidence/content-review.json",
      "sha256": "64 lowercase hexadecimal characters",
      "scope_id": "example-release",
      "source_revision": "approved-plan-r4",
      "artifact_sha256": {"slides": "64 lowercase hexadecimal characters"}
    }]
  }]
}
```

This is an abbreviated, deliberately non-runnable example: add the visual gate and compute real hashes. The tests contain a complete synthetic record and actual raw evidence files.

- `artifacts` is a nonempty inventory of the exact final deliverables. Before auditing, independently reconcile this inventory with the requested output set; omission of an expected deliverable is a review blocker even if the helper succeeds
- `source_revision` is the immutable commit, plan version, or other recorded revision that actually governs this review. Recheck mutable source authority just before the decision
- `required_gates` must include every independently specified `--required-gate`; all listed IDs must exist in `gates`
- Gate results are `pass`, `fail`, `blocked`, or `not_applicable`. Every gate needs a substantive rationale. An NA disposition is a reviewer judgment against the approved scope, not an excuse to omit inspection
- `pass` and `fail` need at least one target artifact and at least one raw evidence file. `blocked` and `not_applicable` can have empty arrays; they still require a rationale
- Every evidence item names the exact current scope and source revision and pins every target artifact to its current hash, with no missing or additional IDs. Its own hash must match the current evidence bytes
- Record raw tool output, rendered page/image observations, calculation checks, or domain-validator results as appropriate. A copied `PASS` label is not sufficient evidence of the underlying check

## Output and limits

Exit 0 means `integrity: verified`; exit 1 means `integrity: invalid`, with errors. CLI misuse is exit 2. `release_decision` is always `not_evaluated`. The output separately reports declared result counts, unresolved gate IDs, and NA gate IDs. An integrity-valid record can contain failures and blockers.

The helper rejects missing files, changed bytes, different scope/revision, missing required gates, unsafe paths, and malformed records. Hashes establish identity only. They do not establish that a check was genuinely performed, that an observation is true, that every required artifact was supplied, or that a recorded rationale is adequate. The independent reviewer must inspect raw evidence, apply the relevant domain checks, justify applicability, and make the final scoped decision.

After any source or final artifact changes, regenerate the affected evidence and rerun the review. Rehashing a stale observation without redoing its check is invalid behavior, even though no general-purpose helper can detect it.
