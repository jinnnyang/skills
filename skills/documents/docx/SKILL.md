---
name: docx
description: "Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx or .dotx files): producing reports, memos, or letters with headings, tables, or page numbers; extracting or reorganizing document content; finding and replacing text (including across split runs); accepting or working with tracked changes (redlining); adding or reading comments; or validating document structure against the OOXML schemas. Trigger on any mention of 'Word doc', 'word document', '.docx', '.dotx', or a deliverable requested as a Word file. Do NOT use for PDFs, spreadsheets, or presentations."
---
# DOCX: create, edit, analyze

A `.docx` is a ZIP archive of XML parts. Pick the approach by task:

| Task | Approach |
|---|---|
| **Create** a new document | `python-docx` (or the `docx` npm lib) — see gotchas below |
| **Edit** an existing document | unpack → edit `word/document.xml` → repack; use `scripts/merge_runs.py` first so text is findable |
| **Read** content | `pandoc doc.docx -t plain` or `python-docx` (`Document(...).paragraphs`) |
| **Accept redlining / add comments** | `scripts/accept_changes.py` and `scripts/comment.py` |

## Scripts

All paths relative to this skill's directory.

| Script | What it does |
|---|---|
| `scripts/office/validate.py` | XSD-validate every XML part against ECMA-376 schemas; check rels resolve and `[Content_Types].xml` covers every part. `--original SRC` baselines errors a source already has |
| `scripts/merge_runs.py` | Merge adjacent runs with identical formatting in `word/document.xml` so find-and-replace can match visible text |
| `scripts/accept_changes.py` | Produce a clean copy with tracked changes accepted, incl. paragraph-mark deletion joining paragraphs |
| `scripts/comment.py` | Add a comment to a docx (directory mode + packed mode), auto-assigning comment IDs, writing the satellite parts and rels |
| `scripts/make_test_docx.py` | Build a minimal VALID test docx from scratch for testing the other scripts |

Dependencies: Python `python-docx`, `defusedxml`, `lxml`; all installed. `pandoc` is
optional (a nicer reader than python-docx but not required). Node is
optional and only needed if you prefer the `docx` npm lib for creation.

## Editing an existing document — the working loop

```bash
mkdir unpacked && cd unpacked && unzip -X ../doc.docx    # -X: no extra attrs
# ... make structural changes first (below), then content edits ...
(cd unpacked && rm -f ../out.docx && zip -Xr ../out.docx .)   # pack from INSIDE the dir
python scripts/office/validate.py out.docx --original doc.docx
```

The main content lives in `word/document.xml`. Most other parts — `styles.xml`,
`settings.xml`, `numbering.xml`, headers, footnotes, comments — hang off it
through `word/_rels/document.xml.rels`. When you add a part you must also add
its relationship and a `[Content_Types].xml` Override, or the file opens broken.
`validate.py` is your backstop for all three.

Do all structural work before editing any paragraph's text.

## The run-splitting problem

Word splits one visible phrase across many `<w:r>` runs — one run per
formatting change, per style edit, or per paste. A find-and-replace that
searches `word/document.xml` for a contiguous phrase usually misses it,
because the phrase is never contiguous in the XML.

Run `scripts/merge_runs.py` first: it folds adjacent runs that carry
byte-identical `<w:rPr>` back into a single run (a run that splits a word at a
formatting boundary is left alone). Then search and replace on the merged text.

**Use `defusedxml.minidom`, never `xml.etree.ElementTree`, when touching
OOXML.** ElementTree rewrites namespace prefixes and corrupts the file;
minidom round-trips prefixes unchanged.

## Tracked changes (redlining)

Word records edits in `word/document.xml`:

- `<w:ins>` wraps inserted runs; `<w:del>` wraps deleted runs (whose text is in
  `<w:delText>`, not `<w:t>`).
- A deleted **paragraph mark** is stored as `<w:del>` inside a `<w:pPrChange>`
  on the following paragraph; accepting it joins the two paragraphs.
- Inserted/deleted runs carry `w:id`, `w:author`, and `w:date`.

`scripts/accept_changes.py` accepts these: it unwraps `<w:ins>`, removes
`<w:del>` (dropping the `<w:delText>`), and joins paragraphs whose mark was
deleted. A known leftover: a list item whose text was fully deleted still
renders its bullet once the text is gone — pass `--drop-empty` to strip
now-blank paragraphs. When you want tracked changes instead, leave the XML
alone and only edit `<w:t>` / `<w:delText>` text, never add or remove runs.

## Comments

A comment spans several parts at once:

- `word/comments.xml` — the comment text (a `<w:comment w:id="N">`).
- `word/commentsExtended.xml`, `commentsIds.xml`, `commentsExtensible.xml` —
  optional modern satellite parts; `commentsExtended` is a harmless Word-2013
  enhancement, the other two are rarely needed.
- `word/_rels/document.xml.rels` — relationships to those parts.
- `word/document.xml` — the markers: `<w:commentRangeStart w:id="N"/>` before
  the annotated text, `<w:commentRangeEnd w:id="N"/>` after it, and a
  `<w:r><w:commentReference w:id="N"/></w:r>` following.

`scripts/comment.py` wires all of these and prints the marker snippet it
inserted. Comment IDs auto-increment from the highest id already present.

## QA — required before delivering

```bash
python scripts/office/validate.py out.docx                       # from scratch
python scripts/office/validate.py out.docx --original src.docx   # from a source
python scripts/make_test_docx.py test.docx && python scripts/office/validate.py test.docx
```

Always pass `--original` when you built the document from a source: the source
often contains parts the XSD itself rejects, and without the baseline a genuine
regression hides among source noise. Structural checks (rels, content types)
always run in full.

**Read-back check** — confirm the visible text is what you meant to write:

```bash
pandoc out.docx -t plain
# or
python -c "import docx; print([p.text for p in docx.Document('out.docx').paragraphs])"
```

**Visual check** — if a human will see this document, render it and look at it.
LibreOffice (`soffice --headless --convert-to pdf out.docx`) or Word. Check for
missing text, orphaned empty paragraphs after accepting changes, and comment
markers pointing at the wrong paragraph.
