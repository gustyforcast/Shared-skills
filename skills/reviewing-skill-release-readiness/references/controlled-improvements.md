# Versioned, approval-controlled improvement

The skill may **observe, review and propose**, not silently rewrite or distribute itself or other skills.

1. **Evidence:** record the exact failed scenario, source revision, observed result and expected result. Never log actual credentials or identifiable individuals' data in public fixtures.
2. **Cause:** separate prompt/instruction failure, unavailable tool, missing input, weak test, external outage and user preference change. Unsupported speculation stays `UNVERIFIED`.
3. **Proposal:** one small change, affected files, benefits, trade-offs, blocked dependencies, and explicit verification plan. Do not mutate an installed release to try an unapproved proposal.
4. **Baseline:** run a no-skill/control or previous-version comparison when feasible. Record what actually fails. Then create an isolated candidate on approval and rerun on the same scenarios.
5. **Independent verification:** structural tests, pressure/application scenarios, release preflight and any domain-specific runtime checks, against the exact candidate. A version label alone proves nothing.
6. **Approval:** the owner explicitly approves the proposed modification and separately approves installation/visibility changes as applicable. If approval is absent, stop at proposal.
7. **Version and rollback:** increment semver appropriately, preserve exact original and digest, record verified regression evidence, and specify rollback. Never auto-publish or auto-merge.

Keep improvement logs short: incident ID, source, evidence, failure, proposed diff, tests performed, approval state and final exact version. Only verified cross-task lessons should become defaults; project-specific exceptions belong in project configuration.
