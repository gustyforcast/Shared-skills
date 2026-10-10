# Asset inspection contract

## Inputs to resolve

Accept the brief and files in normal language, then record:

- `scope_id`, task/stage and exact approved contract revision; source of approval and permitted changes
- Representation for each artifact: flat sprite, layered cutout, 2D puppet/rig, billboard GLB, static 3D, or animated/rigged 3D
- Approved reference/source files, hashes, view identity and provenance; locked identity/features, permitted synthesis and which hidden surfaces may legitimately be inferred
- Required export/native formats, actual final file paths, companion textures/masks/metadata/scenes, intended host/engine and version
- Canvas dimensions and active bounds, units, axis/front/up conventions, expected scale, origin/pivot coordinate convention, trim offsets and padding
- Layer/bone names, hierarchy, draw order, pivots, overlaps, masks, attachments, IK/weights and editable structure where required
- Alpha mode and edge treatment, colour/material requirements, texture dimensions, embedding/path conventions and packaging constraints
- Required poses, actions, frame count/rate/duration, motion/root-motion behaviour, loop and contact requirements; explicit numeric tolerances if supplied
- Intended delivery payload/destination, inspect-only versus authorised modification scope, and the current evidence inventory

Resolve material ambiguity before judging that criterion. A missing numerical tolerance stays unresolved; do not invent a “standard” threshold, universal polycount or acceptable sliding distance. Qualitative requirements may receive a documented visual judgement only when the contract permits it.

## Representation firewall

A reference image specifies appearance only to the extent the approved brief says so. It is not proof of multiple views, hidden geometry, anatomical correctness, a particular rig or authorisation to redesign. A flat cutout is valid when a flat cutout was requested. A textured plane is a billboard, even inside a GLB. A visual-hull reconstruction is a static model unless a rig and animations have actually been delivered and verified. Layers plus pivot metadata do not establish a Skeleton2D/Bone2D hierarchy, working IK or an animation.

For extraction-only work, compare against the locked source and inspect garment/hand/hem boundaries, transparent holes, missing or invented pixels, and any approved hidden-overlap reconstruction. Historical frame sizes and earlier package layer counts are not current defaults.

## Output, in order

1. READY or NOT READY; selected representation, requested stage, target host and exact contract revision
2. Most consequential defect or bounded successful result
3. Final inventory: ID, path, byte length, SHA-256, format and required dependency relationships
4. Gate ledger: ID, PASS/FAIL/BLOCKED/NOT_APPLICABLE, target file hash, exact layer/bone/texture/frame/time/view location, observed evidence, method/tool version, scope and reviewer provenance
5. Required repairs/owner, missing capabilities, unresolved decisions and proof limits
6. Package/export/reimport checks and delivery state; exact payload hashes and verified send reference only when actually sent

A failed import is FAIL with the raw error; an unavailable target host is BLOCKED. A contract-inapplicable rig check can be NOT_APPLICABLE for a flat sprite, with that reason. No required check becomes not applicable simply because tooling is absent. The root shared evidence audit's `release_decision=not_evaluated` remains a structural result, separate from the review verdict.

## Example

Approved brief: “Keep this source unchanged. Deliver separated flat 2D PNG layers on the original canvas, transparent backgrounds and a pivot JSON using pixel coordinates; no rig requested.”

The reviewer compares each layer to the approved source, checks actual canvas dimensions/alpha and placement, reconstructs the layered stack with the supplied pivots/order in an authorised preview tool, and checks the exact export inventory. Bone/IK/gait gates are NOT_APPLICABLE because the contract requests cutouts. A proposal to convert them to a mesh or install Blender exceeds review scope.

If the approved brief instead requires a functioning 2D rig with IK and a walk cycle, the same delivered cutouts fail structural completeness and cannot be released as the requested rig. Missing gait playback evidence also blocks the runtime gate. File naming and an attractive pose preview do not remedy those defects.
