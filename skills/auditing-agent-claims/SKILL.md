---
name: auditing-agent-claims
description: Use when an agent claims work is complete, fixed, passing, deployed, committed, running, or supported by logs and the claim must be independently verified.
---

# Auditing Agent Claims

Treat agent prose as a claim, never as evidence. Verification must bind the evidence to the exact task, repository, worktree, profile, branch, card, artefact and relevant time window.

## Procedure

1. Extract each material claim separately: changed, created, tested, committed, deployed, running, recovered, or evidenced.
2. Define the minimum independent proof before inspecting the claimed evidence.
3. Read back the authoritative source yourself. Prefer filesystem/Git/process/test/API state over summaries written by the worker being audited.
4. Check identity and freshness: exact path, repo/worktree, branch, commit SHA, profile, card/run ID and timestamp must match the claim.
5. Classify each claim as `VERIFIED`, `PARTIAL`, `CONTRADICTED`, or `UNVERIFIED`.
6. Fail closed. A downstream action that requires a verified claim remains blocked until the required proof exists.
7. If evidence conflicts, report the conflict and preserve both sources; do not choose the convenient one without a basis.

| Claim | Minimum proof |
|---|---|
| file changed | exact path plus read-back or hash/diff |
| Git committed | commit SHA plus `git show` and relevant tree/diff |
| tests pass | exact command, exit code and fresh output |
| process running | current process/health evidence with timestamp |
| log proves event | existing log path, relevant lines and matching time/run identity |
| deployed/external | authoritative destination state, not local intent |

## Evidence and output

Return a compact claim ledger with: claim, evidence inspected, identity/freshness check, status, and remaining gap. Cite exact paths, SHAs, run/card IDs, commands and timestamps when available.

Never fabricate logs, infer success from absence of errors, accept a worker-created receipt as independent proof by itself, or use evidence from a different worktree/profile/run. State `UNVERIFIED` when verification is unavailable.
