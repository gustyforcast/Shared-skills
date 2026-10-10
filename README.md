# Shared Skills

Reusable **non-teaching** AI-agent skills. Each skill lives in `skills/<name>/SKILL.md` with its required support files.

| Skill | Purpose |
| --- | --- |
| [`auditing-agent-claims`](skills/auditing-agent-claims/SKILL.md) | Independently verify agent completion claims |
| [`checking-final-artefacts`](skills/checking-final-artefacts/SKILL.md) | Inspect generated documents and deliverables |
| [`workflow-to-kanban`](skills/workflow-to-kanban/SKILL.md) | Create bounded, traceable work items (already shared) |
| [`compressing-prompts-for-local-models`](skills/compressing-prompts-for-local-models/SKILL.md) | Deterministic prompts for smaller local models |
| [`reconciling-stale-pull-requests`](skills/reconciling-stale-pull-requests/SKILL.md) | Review old PRs before rebasing or merging |
| [`extracting-chat-decisions-to-canon`](skills/extracting-chat-decisions-to-canon/SKILL.md) | Extract approved decisions from long discussions |
| [`continual-learning`](skills/continual-learning/SKILL.md) | Evidence-based, approval-controlled skill improvements |
| [`plugin-scout`](skills/plugin-scout/SKILL.md) | Find justified plugin opportunities |
| [`asset-release-inspector`](skills/asset-release-inspector/SKILL.md) | Review sprites, cutouts, rigs and 3D exports |
| [`directing-flux2-klein`](skills/directing-flux2-klein/SKILL.md) | Model-aware prompts and feedback for FLUX.2 Klein |
| [`reviewing-skill-release-readiness`](skills/reviewing-skill-release-readiness/SKILL.md) | Check skill sharing, rights and portability |

## Installation and use

Install an individual skill directory using the official instructions for your agent, or copy it into the agent's supported skills folder. Read its `SKILL.md` and linked references. The skills are instructions and bundled checks; they do not install model runners, Blender, servers, or connectors. A missing host capability must produce a visible BLOCKED or UNVERIFIED result, never invented completion evidence.

The previously shared `workflow-to-kanban` directory is preserved unchanged. The new `continual-learning` and `plugin-scout` source copies are generic and no longer assume any particular user's machine, identity or work. No education-specific skills or creator-specific plans are intentionally included.

## Offline checks

From the repository root, using Python 3.10+:

```bash
python -m unittest discover -s skills/asset-release-inspector/tests -v
python -m unittest discover -s skills/reviewing-skill-release-readiness/tests -v
```

These tests check two bundled deterministic helpers. They do **not** independently test model instruction-following, 3D asset quality, installed tool availability or real production safety. The release-readiness preflight is heuristic and cannot authorise publication.

## Licence status

The owner has authorised source sharing here, but **has not yet selected a repository-wide public reuse licence**. Public readability does not automatically grant permission to republish, modify or distribute copies. Existing third-party references retain their respective rights. Selecting a licence and independent end-user testing are separate release-readiness steps.
