# Evidence-led release gates

Apply these to the **exact final bytes and intended release channel**. A private skill used on one machine has different requirements from a public distribution. Every gate still needs a named result; `NOT_APPLICABLE` must be explained. The reviewer's judgement is not a substitute for legal or security expertise.

| Gate | Evidence for PASS | Common FAIL or BLOCKED | Minimum fix |
| --- | --- | --- | --- |
| VALUE_AND_OVERLAP | Identified users/tasks, repeated durable workflow, comparison with existing skills, unique benefit | No meaningful extra capability; unsupported audience/demand claims | Narrow purpose, merge with an existing skill or keep private |
| VERSION_AND_PROVENANCE | Exact source commit/tree, final ZIP digest, manifest/version parity, changelog and release ID where relevant | Branch differs from plugin, old ZIP, mixed versions or unknown source | Freeze a single revision, rebuild and compare hashes |
| PRIVACY | Full candidate inspected for real secrets, individuals' information, internal paths and sensitive attachments; documented permission for any retained personal material | Token or identifiable student/work content; hidden source or incomplete review | Remove or redact, rotate compromised real credentials, then re-scan |
| RIGHTS | Owner-selected distribution licence plus supported rights/provenance for third-party source, images, fonts, code, examples and third-party assets | Absent licence, unknown extract provenance, conflicting terms or inadequate evidence | Remove/replace restricted material or obtain specific rights confirmation |
| PORTABILITY | Tested on a fresh environment without creator memory, hardcoded local paths, private accounts or hidden default data | Assumes one class, user's name, Windows profile, local model/server or private repo | Parameterise configuration, add examples and a blocked fallback |
| DEPENDENCIES | Real tools/runtimes/APIs and versions listed; clean install or accepted no-tool fallback demonstrated | Missing executable, unconnected plugin, unverified runtime, undocumented credentials | Document precise prerequisites and verify a supported host |
| PERMISSIONS_AND_SAFETY | Read/write boundaries, side effects, confirmation gates, offline/network behaviour and credential handling inspected and tested | Destructive operations, auto-updates or external publishing without approval | Remove implied permissions, require specific approval and test failure modes |
| DOCUMENTATION | Selective skill trigger, current README, setup/use/output contract, examples and limitations match actual package | Missing or misleading instructions, unfindable SKILL.md, broken links | Repair docs and verify from a clean copy |
| BEHAVIOUR | Independent real-world tests including negative/pressure cases, with baseline/control where appropriate and reproducible evidence against current version | Only self-reported success, static tests alone, stale CI, untested classroom output | Run independent pressure and application tests; preserve actual outputs |
| CONTROLLED_IMPROVEMENT | Verified defect log, minimal proposed diff, red/green checks, versioned changes, and explicit approval boundary | Silent instruction edits, autonomous publishing or self-certified improvements | Gate all change/release actions behind approval and fresh revalidation |

## Decision rule

- `READY_FOR_OWNER_DECISION`: all applicable gates PASS, and release process is waiting for explicit owner approval or an authorised release action.
- `HOLD`: any material gate FAIL for the intended channel. Do not publish or install it for other people as though safe.
- `INSUFFICIENT_EVIDENCE`: no material FAIL has been established but essential evidence/independent checks are BLOCKED or inaccessible. A strong review summary does not turn a BLOCKED into PASS.

A technical preflight can only contribute evidence to these gates. It does not award human or legal PASS. For a private draft, N/A may be legitimate for public listing metadata, but a missing dependency that stops private use is still a blocker.

## Minimal review record

```text
CANDIDATE: <actual source> @ <SHA/digest> | version | package/release ID
TARGET: <private / named collaborators / source / public listing>
AUDIENCE AND VALUE: <factual evidence, overlap, limitations>
GATES: <name> | PASS/FAIL/BLOCKED/NOT_APPLICABLE | exact evidence | minimal repair
VERDICT: READY_FOR_OWNER_DECISION / HOLD / INSUFFICIENT_EVIDENCE
OWNER ACTION: <specific proposed write/install/share/publish requiring approval>
```
