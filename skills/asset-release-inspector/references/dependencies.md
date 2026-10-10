# Tool reuse and capability boundary

This skill provides instructions and role cards. It installs no 2D/3D editor, engine, Python package, model server, image generator, Blender runtime, plugin or scheduler. Tool availability must be checked in the host where the asset actually lives. A requested local-computer task follows the host's supported delegation/connection route; missing tools in the coordinator do not establish that the user's computer lacks them.

## Discover before invoking

The following existing script names are useful candidates from asset workflows, not bundled or guaranteed commands:

- `inspect_model`
- `validate_character_release`
- `inspect_assets`
- `validate_sprite`
- a sprite-preview utility

Resolve each through the selected project's documented source, installed skill or authorised repository. Inspect source/help and file identity before execution. Record path, version/hash, supported formats, parameters, outputs and side effects. Do not guess command-line flags or invoke an unrelated tool just because its filename matches. Do not treat these names as fixed paths on another computer. If no verified tool is available, use an appropriate already-authorised host reader for the bounded inspection and explicitly block unperformed checks.

Prefer these existing tested inspectors when they cover the actual contract. Do not blindly reimplement a mesh/rig/sprite validator. A new deterministic helper is justified only by a demonstrated uncovered requirement and requires independent synthetic fixtures, tests and a narrow proof statement. A geometry/metadata parser cannot certify visual fidelity or animation quality.

## Safe inspection

Inspect source files as data. Do not execute embedded scripts/macros, auto-run project code, fetch missing remote textures or install dependencies merely to open a package. If the target host requires an action outside review authority, pause that step and request the exact permission. Use non-destructive copies and a new evidence directory for previews/exports; preserve originals and source provenance.

A tool may mutate files even when named “preview” or “validate”; read its behaviour first. Use its read-only mode if verified. Import roundtrips must occur in an isolated inspection copy and require the available authorised target host. Do not launch Blender, a model service or an engine automatically when capability is missing.

## Shared and domain references

Use the separately available `checking-final-artefacts` skill for actual-delivery, cross-file and package integrity. Apply the current selected project's puppet/sprite/model contract; do not copy private project calibration into this reusable plugin. Historic cutout, billboard and 3D workflows have different requirements and are not interchangeable defaults.

Use `skills/asset-release-inspector/scripts/audit_evidence.py` from the shared repository root and [shared evidence contract](evidence-contract.md) for supplementary hash/scope checks. Supply `--scope-id`, `--source-revision` and repeated `--required-gate` flags from the approved contract and this skill's gate catalogue, not from a producer's convenient list. The helper never interprets images or certifies target runtime behaviour; its `release_decision=not_evaluated` is not a failed capability and must not be rewritten as PASS.
