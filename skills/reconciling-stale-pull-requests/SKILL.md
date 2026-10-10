---
name: reconciling-stale-pull-requests
description: Use when reviewing, rebasing, closing or merging stale or diverged pull requests, especially when branches are behind main, PRs overlap, behaviour may already be present, or CI is historical, zero-step or otherwise ambiguous.
---

# Reconciling Stale Pull Requests

## Core Contract

Use three phases in order. **Phase A must finish with a disposition before Phase B may begin.**

## Phase A — Read-Only Disposition

Inputs: exact target SHA/tree, exact PR head SHA, merge-base, changed files, PR intent, current contracts/decisions.

Work only against the untouched target and the old PR as read-only evidence:

1. Inspect the PR diff/commits to identify the claimed behaviour.
2. Inspect current target for equivalent or superseding behaviour.
3. Reproduce the claimed gap on the **untouched target** using existing checks or a new regression that runs only against target code.
4. Output exactly one disposition:
   - `ALREADY_PRESENT`
   - `STILL_REQUIRED`
   - `SUPERSEDED`
   - `CONFLICTING`
   - `INSUFFICIENT_EVIDENCE`

**Phase A never applies, cherry-picks, rebases, merges, patches, or executes old-PR code in any branch, including temporary test branches.** Preserve the old head unchanged.
## Phase B — Fresh Candidate

Enter Phase B **only** for `STILL_REQUIRED`.

Create a fresh branch/worktree from the pinned target. Port only the required behavioural delta from the old PR. Preserve the Phase-A regression: RED on untouched target, GREEN on candidate. Validate from a clean checkout with relevant build/typecheck/package, deterministic contracts and runtime checks.

For `ALREADY_PRESENT` or `SUPERSEDED`, record evidence and close unmerged. For `CONFLICTING` or `INSUFFICIENT_EVIDENCE`, stop mutation and preserve evidence.

## CI Evidence

- Historical green proves only its historical SHA.
- A current test that executes and fails is negative code evidence.
- A job that fails with **zero executed steps** is infrastructure/configuration evidence, not application-code failure.
- Local equivalents can establish code evidence but never silently satisfy a required hosted gate.

## Phase C — Combined Integration

When multiple surviving candidates are related, create an isolated integration branch from the exact target and combine them in dependency/overlap order. Run the full relevant suite on the **combined state**. Individual green PRs are insufficient. If combined verification fails, merge none.

## Protected Merge

After owner approval:

1. Re-read each PR and confirm the expected head SHA.
2. Merge only the integration-tested order using expected-head/SHA guards where supported.
3. Never force-push merely to make a stale PR look current.
4. Re-run release-relevant verification on the actual forge-generated target SHA.

Completion records must include target SHA/tree, PR heads/dispositions, exact checks and limitations, combined-integration result, unresolved hosted gates, and verified post-merge target SHA.
