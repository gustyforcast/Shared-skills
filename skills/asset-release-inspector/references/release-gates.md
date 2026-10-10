# Conditional asset gates

Derive required gate IDs from the approved representation and target contract before reading producer verdicts. Preserve every base gate; mark genuinely irrelevant conditional work NOT_APPLICABLE with a contract citation. Add named contract-specific gates when needed. Do not silently lower the approved quality level.

| Gate ID | Required evidence and scope |
| --- | --- |
| `contract_reference` | Current approved source/contract, representation, target versions, tolerances, locked features and permitted changes are identified and accessible |
| `artifact_integrity` | Every required native/export/companion file exists, opens, is nonempty and has measured bytes/hash; actual type matches its declared role |
| `reference_fidelity` | Source-to-final visual comparison in required views shows approved identity, silhouette, proportion, colours, crop and extraction fidelity |
| `dimensions_coordinates` | Actual dimensions, active bounds, padding, units, axes/front/up, scale, origin, trim offset and pivots match the contract |
| `alpha_materials` | Required alpha channel/transparency really exists; no opaque checkerboard/background, unintended holes/halos or missing textures; material/colour/export settings match target |
| `layers_structure` | Required layer names/count/order, masks, overlap and complete editable native structure are present. Conditional on layered deliverables |
| `rig_structure` | Required actual bones/hierarchy, rest pose, pivots, attachment/weight/IK constraints and control semantics exist and work. Conditional on rigged deliverables |
| `pose_deformation` | Required pose tests show correct articulation, occlusion, overlap, handedness, limits and deformation without separations or clipping. Conditional on posed/rigged claims |
| `animation_contact` | Required actions, timing, full-cycle continuity, transitions, gait/support phases, foot contact and root motion meet contract; frame/time evidence retained. Conditional on animated claims |
| `target_roundtrip` | Export/import in the specified available target host preserves geometry/scale, materials/alpha, pivots/bones/actions and dependency resolution. If interoperability is promised, this is required |
| `provenance_preservation` | Source origins and authorised transformation history recorded; originals untouched; generated/reconstructed content clearly identified; no unsupported authorship/licence claim |
| `delivery_payload` | Correct final filenames, dependencies, previews/metadata when requested, archive membership and byte hashes; no unintended draft, credential, local absolute path or stale asset |

## Flat sprites and layered cutouts

- Inspect actual file dimensions and alpha data, not a thumbnail or checkerboard appearance. Show composites on contrasting backgrounds using available authorised inspection tools; edge halos can be invisible on one background
- Distinguish full-canvas and trimmed layers. Validate trim offsets and pivot coordinate convention, then reconstruct alignment in a copy. Do not crop, resize, recolour or fill hidden areas merely to make the preview look plausible
- Check locked-source boundaries and all specified overlap zones: joints, shoulders, sleeves, hands, hem and occluded pieces. No missing visible pixels, duplicated anatomy or unsupported reconstructed detail
- Validate layer names/order and masks by the actual composition, not a list count. A pivot inside a JSON file is only metadata until the intended host uses it correctly

## 2D puppets and rigs

- Inspect the actual target scene/rig structure: bones, hierarchy, pivots, attachment/weight rules, IK and control naming required by the contract. A folder of separated images is not a functioning rig
- Check rest pose and required extreme poses at full size. Test hinge centres, joint coverage, overlaps/draw order, hand variants and attachments without destructive changes to the source
- For a walk/run/cheer cycle, inspect the full action and all transitions named in scope. Record required frames/times and motion phase. Check grounded support-foot stability, lift, landing, contact height, sliding, penetration and plausible weight transfer within approved tolerances
- Distinguish in-place versus root-motion animation. A moving root can be correct; compare contact in the required coordinate frame. Keyframe existence or three still poses cannot certify a full gait

## Billboard, static 3D and rigged 3D

- A billboard's plane, transparency, double-sided/unlit material, anchor and scale are checked only where required by that billboard contract. Its planar geometry is not a defect when a billboard was requested
- For a static mesh, inspect approved views, silhouette/depth, units/axes, transforms, nonempty geometry, normals and texture/material paths. Require watertightness/manifoldness/topology or polycount budgets only when the actual use contract needs them
- Multi-view references must be the supplied approved views, aligned as required. A reconstruction cannot claim observed detail in unseen regions; record inferred geometry and whether it is authorised
- For a rigged model, inspect real skin/bone bindings, hierarchy/rest pose, required joint deformation, actions and target import. Missing embedded textures or broken relative resources fail self-contained delivery claims
- No blanket Blender requirement applies. Use an already available authorised compatible host; if the required runtime is absent, block that evidence rather than install/start it or substitute an unrelated preview

## Evidence and changes

For every measurement include file hash, location, coordinate convention/units, method, observed value and contract expectation. For every visual/runtime judgement include the inspected view/frame/time and raw capture/log path. Retain the full required coverage index, not only favourable samples. An engine-import claim needs the actual target/version and observed outcome.

The shared auditor can verify hashes and scope, but cannot infer whether a foot slides, a face matches, a bone is correctly weighted or a layer overlap is sufficient. Its clean result is not release approval. Any changed native or export file invalidates evidence bound to its old bytes; refresh dependent textures/rig/animation/export checks and hash the actual delivered payload.
