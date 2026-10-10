---
name: asset-release-inspector
description: Use when sprites, layered cutouts, puppets, rigs, animations, textures or 3D asset packages need review against an approved reference and export contract before handoff, especially when a generated preview is claimed to prove a working asset.
---

# Asset release inspector

Inspect the delivered asset against the approved contract and real runtime evidence. A convincing image, file extension or success log cannot prove editable layers, a rig, a gait or a complete 3D model.

## Establish the target

1. Read [input/output contract](references/input-output-contract.md), [conditional gates](references/release-gates.md) and [tool reuse](references/dependencies.md).
2. Identify the approved reference/source revision and representation: flat sprite, layered cutout, 2D rig, billboard, static 3D or rigged/animated 3D. Use separate artifact records for mixed packages. Never infer a 3D or rig requirement from a reference image, or treat cutouts as a fulfilled rig request.
3. Freeze required deliverables, dimensions/units, origin/pivots, layer/bone naming, textures/alpha, poses/actions, target host/version, tolerances and permitted edits from the actual approved contract. Ask about material gaps; do not carry dimensions or artistic decisions from another project.
4. Inventory actual final files and bytes with SHA-256. Preserve approved originals. Work read-only or on separately named inspection copies; never overwrite source, destructively bake transforms or repair and self-certify.

## Inspect

Use the bounded [release-inspector role](agents/roles/release-inspector.md). Compare final visual identity, silhouette, proportions, alignment and extraction boundaries with the exact approved source. Check dimensions, canvas/crop, coordinate system, scale, anchor/pivots, naming, layers, masks, bones, weights, materials, texture resolution and alpha only as required by that representation.

Find verified existing inspection tools before writing another parser. Read their source/help, supported inputs, version and side effects. Candidate names include inspect_model, validate_character_release, inspect_assets, validate_sprite and a sprite-preview utility; names alone do not verify their existence or suitability. No tool installation, Blender dependency, model/image generation service or startup action is supplied or implied.

When the contract requires poses, animation or engine import, use [the pose/runtime role](agents/roles/pose-runtime-reviewer.md) with an available authorised host. Inspect the required actions, full gait cycle, transitions, loop seam and foot contact against contract tolerances. Static images cannot prove motion, deformation or engine compatibility. Missing capabilities leave those gates BLOCKED.

## Release decision

Return READY only when every applicable gate passes for the approved representation and exact final bytes. Otherwise return NOT READY with located defects, missing evidence and minimum corrections. Keep mechanical structure, visual fidelity, runtime behaviour, provenance and delivery findings separate. Follow the [shared evidence contract](references/evidence-contract.md) with required gate IDs derived independently from the approved brief. Its audit checks binding integrity, never artistic or runtime correctness.

Route fixes to the owner; preserve earlier evidence and re-inspect revised files. Verify the exported/reimported payload and every required dependency, then hash the exact delivery bytes. Distinguish an inspection-ready recommendation from an actual delivery receipt. Review-only authority does not permit publishing, changing permissions, executing untrusted embedded code or installing/starting software.
