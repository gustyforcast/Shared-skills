---
name: checking-final-artefacts
description: Use when a generated PDF, PowerPoint, Word document, spreadsheet, or other deliverable is about to be released and needs independent content, rendering, and package quality assurance.
---

# Checking Final Artefacts

Review the deliverable that the user will actually receive, not only the source used to generate it.

## Procedure

1. Restate the required deliverables, filenames, formats, page or slide size, and any content or version relationships that must hold.
2. Confirm every requested file exists and opens in the intended final format.
3. Inspect the final rendered pages, slides, sheets or document views. Check clipping, overflow, overlap, missing assets, tiny text, broken symbols, unexpected blank pages, distorted images and inconsistent spacing.
4. Check content completeness against the brief. Verify titles, instructions, answers, totals, labels, dates and other high-risk fields rather than assuming successful export preserved them.
5. Where deliverables are paired, compare them directly. Student/teacher versions, source/export versions, worksheets/answers and related files must remain synchronised where required.
6. Check package hygiene: correct filenames, no unintended drafts, temporary files or duplicate stale outputs, and no missing required companion files.
7. If a defect is repaired during the same task, rerun the affected checks on the new final artefact. A pre-fix inspection cannot certify a post-fix file.
8. Do not classify a warning as harmless without inspecting the affected location.

## Evidence and output

Return a release ledger with `PASS`, `FAIL`, or `BLOCKED` for: deliverable presence, file integrity, required dimensions, content completeness, rendered readability, visual containment, asset integrity, cross-file consistency, and package hygiene.

For every failure, identify the exact file and page, slide, sheet, or location when available.

Return `READY` only when every applicable gate passes. Otherwise return `NOT READY`.

A successful save, export command or generator log is not evidence that the final artefact is visually or substantively correct.
