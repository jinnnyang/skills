# pptx

Create, edit, and analyze PowerPoint decks (.pptx/.potx): unpack-edit-repack,
slide duplication/reordering, template filling, validation.

| Field | Value |
|---|---|
| Origin | Original work (SKILL.md, scripts, validators) |
| License | Apache-2.0 (see `LICENSE.txt`) |
| Notable third-party content | `scripts/office/schemas/` — verbatim ECMA-376 / W3C standard XSDs; `mc.xsd` from docx4j (Apache-2.0). Notices in `scripts/office/schemas/SCHEMAS-LICENSE.md` |
| Reference material | Anthropic's `document-skills/pptx` was reviewed for domain context only (source-available, not redistributable, no content included). Local copy: `Documents/anthropics-skills/reference/document-skills` |

## For developers

- Same architecture as `documents/docx`: unpack → edit XML → `validate.py` → repack.
- Do not copy from the Anthropic reference copies; extend per the
  `ooxml-skill-authoring` skill's license gates.

