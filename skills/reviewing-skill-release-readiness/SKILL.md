---
name: reviewing-skill-release-readiness
description: Use when deciding whether an AI skill or plugin is ready to share, install elsewhere, submit publicly, or release a revised version; especially when privacy, licences, stale versions, untested behaviour or local dependencies may block distribution.
---

# Reviewing Skill Release Readiness

**Core rule:** assess the actual, pinned distribution candidate, not its reputation, README claims or a previous successful run. A technically valid package is not evidence of legal clearance, real behaviour or permission to publish.

## Start with the release target

1. Establish the user's objective: **private install**, **share with named colleagues**, **publish source**, **public plugin submission** or **update an existing release**. These targets require different evidence; do not quietly escalate scope.
2. Identify the source of truth and exact candidate (repository/commit, directory, or ZIP SHA-256), installed plugin ID/release if relevant, target hosts, intended audience, owner, expected use and explicitly permitted actions. Where multiple variants exist, reconcile them; never assume a public branch and installed package contain the same skill.
3. Obtain the actual files or authorised read-only access. If only names, descriptions or snippets are visible, return `INSUFFICIENT_EVIDENCE` and request the smallest missing source. Do not invent tests, installation access, rights or user consent.

## Evaluate independently

Read [release gates](references/release-gates.md). Record a separate `PASS`, `FAIL`, `BLOCKED` or `NOT_APPLICABLE` for **value/overlap, source and version, privacy, distribution rights, portability, dependencies, permissions/safety, documented usage, tested behaviour and controlled improvement**. Every PASS needs evidence bound to the exact candidate and target release. `NOT_APPLICABLE` needs a reason. Never average away a release blocker.

If Python 3.10+ and the source are available, run the optional *read-only heuristic* preflight:

```bash
python skills/reviewing-skill-release-readiness/scripts/preflight_release.py /path/to/candidate-folder-or-zip
```

Resolve the command relative to the plugin package root in the current environment. Use actual returned findings only. The checker doesn't upload, extract, publish, change files or contact services. It checks structure, likely secrets/contact details, some local paths, licence presence, basic version consistency and test-file presence. **A clean scan NEVER establishes readiness.** Without Python, perform a transparent manual review and mark unperformed automated checks `BLOCKED`.

Verify material claims with available independent means: open the final ZIP/files, compare SHA-256 and manifest versions, trace copied text/assets to rights evidence, inspect examples and any personal information, follow installation instructions in a clean supported host, and rerun the relevant behavioural scenarios. Use [pressure scenarios](references/pressure-scenarios.md) as a starting point. Merely listing tests or showing historical green CI is not enough. Do not present a self-generated agent message as independent evidence.

## Decide and report

Return in this order:

1. **Candidate:** exact source, version, immutable identifier, release target and audience.
2. **Reuse value:** `HIGH`, `MODERATE`, `LIMITED` or `UNASSESSED`, with concrete audience, differentiated workflow and overlap evidence. Do not invent demand or downloads.
3. **Gate ledger:** gate, `PASS/FAIL/BLOCKED/NOT_APPLICABLE`, source evidence or exact missing evidence, and shortest repair.
4. **Verdict:** `READY_FOR_OWNER_DECISION` only if all applicable gates really pass; `HOLD` for a material FAIL; `INSUFFICIENT_EVIDENCE` for missing essential checks. A ready verdict is not the owner's publication approval.
5. **Next actions:** the smallest safe fixes, tests, packaging steps and explicit approvals still needed. Distinguish **creation**, **installation**, **sharing** and **public publication**.

For sharing or public release, missing ownership/permission evidence, an exposed credential, disallowed third-party material, or insufficient behaviour validation is a release barrier. General coding/skill conventions alone do not establish licence rights or end-user output quality. Avoid making legal determinations: identify evidence needed for rights review.

## Self-improvement boundary

After a real review, capture **verified** defects, root causes and reusable lessons. Propose a small versioned change with before/after checks and a clean regression run. **Never change skill instructions, copy private content into examples, install an update, enable a tool, share a package or publish it without specific owner approval for that action.** User approval to create this reviewer is not blanket approval for future updates. Read [controlled improvements](references/controlled-improvements.md).

## Stop conditions

When source files, independent tests, rights evidence, required hosts, or owner permission are unavailable: report the exact blocked gate and useful read-only findings. Never substitute a favourable guess, re-label old test results as current, or silently create a public release.
