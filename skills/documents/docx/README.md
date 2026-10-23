# docx

Create, read, edit, and analyze Word documents (.docx/.dotx) — including tracked
changes, comments, and OOXML schema validation.

| Field | Value |
|---|---|
| Origin | Original work. Design was informed by reading Anthropic's `document-skills/docx` (source-available, **not** redistributable — no code or text from it is included) |
| Reference | https://github.com/anthropics/skills/tree/main/skills/docx (local reference copy: `Documents/anthropics-skills/reference/document-skills/docx`) |
| License | Apache-2.0 (see `LICENSE.txt`) |
| Notable third-party content | `scripts/office/schemas/` — verbatim ECMA-376 / W3C standard XSDs, notices in `scripts/office/schemas/SCHEMAS-LICENSE.md` |
| Bundled variant | Hermes ships a separate, unrelated implementation at `%LOCALAPPDATA%/hermes/hermes-agent/skills/productivity/docx` (MIT, Nous Research) — different scripts, different architecture |

## For developers

- Every sentence and script was written from OOXML knowledge, not adapted from
  Anthropic's source-available skill. Do not copy text or code from the local
  reference copy into this repo.
- Validation chain: `scripts/office/validate.py` XSD-validates every XML part.
- See `ooxml-skill-authoring` skill (in `skills/documents/`) before extending.

