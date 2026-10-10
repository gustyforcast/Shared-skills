# Using directing-flux2-klein V1

Invoke `$directing-flux2-klein` with the actual image request and selected model, for example:

> Use $directing-flux2-klein to draft a prompt for Klein Base 4B: a coastal library with one central fountain and two rear staircases. Prepare the prompt only.

Use your normal generation workflow separately when you are ready. Then attach or link its image and provide feedback:

> Keep the stonework and lighting. Move the staircases to the rear and remove the extra fountain. Revise the existing prompt; don't generate yet.

The skill preserves what you liked, records the revised attempt and keeps that correction local. If the same preference appears in independent image tasks, it can become scoped reusable guidance in the project log. Copy `assets/feedback-log.md` into the project; the template itself stays blank.

For ChatGPT without Codex skills, provide `SKILL.md` and `references/model-notes.md` as instructions and use the feedback template in the conversation or project. This is a portable instruction workflow, not verified ChatGPT-product integration.

V1 has lightweight package and instruction-workflow checks. It does not include a generation backend, inspect unavailable images, automatically learn from unrelated projects, or establish comprehensive image-quality validation. Historical research is provisional. No new images are required to use or verify the instruction-only workflow.
