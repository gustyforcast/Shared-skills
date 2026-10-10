---
name: extracting-chat-decisions-to-canon
description: Use when a long chat, design discussion, or project thread must be reduced to the decisions that became authoritative, with proposals and superseded ideas excluded from canon.
---

# Extracting Chat Decisions To Canon

Conversation contains exploration as well as decisions. Do not promote an idea merely because it was discussed repeatedly.

## Procedure

1. Identify the scope being canonicalised: feature, world area, workflow, visual standard, architecture or other bounded topic.
2. Read the relevant discussion in chronological order when possible.
3. Classify each material statement as:
   - `APPROVED`: explicitly accepted or clearly adopted by the user;
   - `PROPOSED`: suggested but not accepted;
   - `SUPERSEDED`: once accepted but later replaced;
   - `REJECTED`: explicitly declined;
   - `UNRESOLVED`: discussed without a settled decision.
4. Treat later explicit user corrections as higher authority than earlier decisions. Assistant proposals are not canon unless the user accepted them or authoritative project evidence shows the decision was adopted.
5. Separate stable decisions from implementation details that were merely convenient in one attempt.
6. When repository canon is also supplied, compare the approved chat decisions with it. Report conflicts rather than silently choosing or merging.
7. Build the canon candidate from `APPROVED` decisions only. Preserve exact names, constraints, boundaries and negative decisions that materially limit future work.
8. Do not edit project canon unless the user explicitly requested the write.

## Evidence and output

Return:
- a decision ledger with status and supporting conversation evidence;
- a concise canonical decision set containing only current approved decisions;
- superseded or rejected decisions that future work must not revive;
- unresolved questions;
- a repo-update plan or patch only when requested.

Never convert brainstorming, assistant inference, unanswered questions or repeated wording into an approved decision.
