# ooxml-skill-authoring

Meta-skill for building or fixing *original* docx/pptx/xlsx skills in this repo:
license gates, schema sourcing rules, validation chain.

| Field | Value |
|---|---|
| Origin | Original work, authored in-repo from this project's own licensing decisions |
| License | MIT (repo default) |
| Key external facts it encodes | Ecma International copyright policy (XSD redistribution with notice), docx4j Apache-2.0 mc.xsd, Anthropic document-skills are source-available/non-redistributable |

## For developers

- Read this before creating any new `skills/documents/*` skill or touching
  schemas — it prevents license violations (e.g. accidentally committing
  Anthropic's source-available text).

