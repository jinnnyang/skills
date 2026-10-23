---
name: ooxml-skill-authoring
version: 1.0.0
author: Hermes Agent
license: MIT
description: "Use when building or fixing original docx/pptx/xlsx skills."
metadata:
  hermes:
    tags: [ooxml, docx, pptx, skills-repo, licensing]
---

## When to Use

- Building a new original document skill (docx/pptx/xlsx/pdf) in `Documents/skills`
- Fixing or extending `skills/documents/*` — schema questions, validation chain, licensing
- Deciding what may be committed from Anthropic-derived reference material

# Authoring Original OOXML Document Skills

Builds original document skills (docx/pptx/xlsx/pdf) for the user's skills repo (Documents/skills, github jinnnyang/skills). Two skills already exist as architecture references: `skills/documents/pptx` and `skills/documents/docx` — study them first and copy their structure.

## License gates (do these before writing anything)

- Anthropic's original document-skills are source-available: never commit them, their text, or derivatives to any public repo. Local reference copies live in `Documents/anthropics-skills/reference/document-skills/` — read them to learn the domain, then write every sentence and script from OOXML knowledge, not by adapting theirs.
- XSD schemas: use verbatim copies from the official ECMA-376 downloads page (ecma-international.org → standard page → edition zips). Ecma's copyright policy permits redistribution with notice; the schemas dir must carry `SCHEMAS-LICENSE.md` stating sources. Verify the copies are byte-identical (modulo CRLF) to the official files with `diff <(tr -d '\r' < a) <(tr -d '\r' < b)` — never take schemas from a third-party repo without that check.
- Do not bundle Microsoft extension schemas (microsoft/wml-*.xsd) unless a validator actually references them; their XSD redistribution terms are unverified. For small ones (some are ~14 lines), writing them from the [MS-DOCX] / [MS-ODRAWXML] Learn documentation is the clean path.
- mc.xsd: use docx4j's `markup-compatibility-2006-MINIMAL.xsd` (Apache-2.0) rather than Anthropic's modified copy.
- W3C `xml.xsd`: take the 2001-03 variant (`https://www.w3.org/2001/03/xml.xsd`) — later versions embed XHTML and mismatch imports.

## Architecture (copy from the existing skills)

- `scripts/office/pkg.py`: shared package surgery (safe_extract with traversal protection, atomic rezip with `[Content_Types].xml` first+stored, RelsFile, content-type helpers, defusedxml minidom round-trips).
- One validator (`office/validate.py`): XSD pass + structural pass (rels resolve, rIds unique, content-type coverage), `--original` baselining for template-derived files.
- `make_test_<fmt>.py`: build a minimal VALID fixture from scratch — the only test input that needs no binary.
- Parsing: defusedxml minidom only. ElementTree rewrites namespace prefixes and corrupts OOXML. Namespace-qualified attributes need `setAttributeNS(ns, 'pfx:name', v)` — plain `setAttribute('r:id', ...)` drops the attribute on serialize.

## Validation chain (run before every commit)

1. `python skills/meta/skill-creator/scripts/quick_validate.py skills/<category>/<name>` — frontmatter gates (needs PyYAML installed).
2. Build the fixture, run the validator, run every script's full operation, re-validate after each — a script that writes invalid XML must fail the chain, and each fix gets a re-run, not a one-off patch without retest.
3. Open outputs with python-docx / python-pptx as the independent reader.
4. `python scripts/gen_marketplace.py` at repo root (regenerates `.claude-plugin/marketplace.json`); `--check` mode for CI.

## Content-type strings (memorize)

Main document parts end in `+xml` (e.g. `...presentationml.slide+xml`); only the package-level presentation part is `...presentation.main+xml`. python-pptx/python-docx refuse to open a file whose main-part content type lacks `.main`.

## Schema element-order traps

OOXML sequences are order-enforced: `w:pPr` must be the first child of `w:p` (insert markers like `w:commentRangeStart` AFTER it); `<w:del/>` inside rPr comes before the rPr's other children. When a validator reports "element not expected", check insertion position before suspecting the schema.

## Rendering for visual QA

soffice → PDF → pdftoppm/PyMuPDF is the generic path. On Windows with MS Office but no LibreOffice, PowerPoint COM automation (pywin32, `SaveAs(pdf, 32)`) renders pptx; pymupdf substitutes for pdftoppm. Make renderers optional with graceful fallbacks — the machine's toolset varies.

## Delegation note

For whole-skill builds the user may ask to delegate to prime-agent — see the prime-agent skill's references/best_practices.md for the validated brief-file + verify-externally pattern. Self-reported "tests pass" from a delegated run must be re-run manually; delegated builds have shipped schema-order bugs and placeholder frontmatter behind passing self-tests.
