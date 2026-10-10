# Model compatibility and provisional research

These are captured documentation and local observations from 3 October 2026, not a promise about every installation. Check the selected backend's exposed fields before execution. Do not load a model or change runtime configuration merely to draft a prompt.

| Variant | Captured upstream defaults | Interpretation |
| --- | --- | --- |
| FLUX.2 Klein distilled 4B | 4 steps, guidance 1.0; upstream fixes both | Do not recommend Base-style guidance/step tuning as a supported distilled control. |
| FLUX.2 Klein Base 4B | 50 steps, guidance 4.0; adjustable upstream | Defaults, not measured optimal settings. Preserve the user's established settings. |

The study used separate local profiles with these values. Field names differ by backend (for example `guidance` versus `cfg_scale`); don't assume aliases are interchangeable. Other Klein variants need their own confirmed model configuration.

Captured official Klein guidance documents up to four reference images and no prompt upsampling. Reference limits apply to the selected route; a text-only wrapper may expose no editing despite model-family documentation. Local Lemonade tests returned valid files for one through four reference inputs on both tested 4B profiles. Transport success does not prove every reference was faithfully used or preserved. Masks and arbitrary ordering semantics are not established by those tests.

BFL's captured FLUX.2 help guidance says negative prompting is unsupported. Keep exclusions in the visual contract and express intended visible states without losing their meaning; do not add an invented API field. Describing desired states is optional prompting guidance, not established causal benefit.

Specify observable camera/composition intent in ordinary terms. Exact physical pitch, focal length, time of day and hidden geometry cannot be proven from an image alone. Subject ordering, prose syntax, repetition, verbosity and spatial phrasing remain provisional; no preferred word count or comprehensive image-benefit result was established by the historical programme.

## Provenance

- [BFL model configuration](https://github.com/black-forest-labs/flux2/blob/main/src/flux2/util.py), captured 3 October 2026. Snapshot SHA-256: `ab39e974b1f696f9d51cb64eef9d82086c683771ac63e7ef14b30cced4b089e0`.
- [BFL Klein guidance](https://github.com/black-forest-labs/skills/blob/master/skills/flux-image-best-practices/rules/flux2-models.md), captured 3 October 2026. Snapshot SHA-256: `a25e6d7b40eff9661aabd5d9853ce7b04600c62502a3aadfff8d3fa37352a304`.
- [BFL negative-prompting help](https://help.bfl.ai/articles/7734566352-does-flux-2-support-negative-prompting), captured 3 October 2026 in the preserved research addendum.
- Historical local test files are not distributed with this skill; those observations are not independently reproduced by a new user.

Local evaluators qualified some constructed-fixture capabilities and failed others. Calibration and image counts do not prove that this skill improves images. Holdouts were not used to develop this V1. Future learning should come from concrete user requests and recorded feedback, without reviving the old benchmark as a prerequisite.
