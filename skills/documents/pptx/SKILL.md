---
name: pptx
description: "Use this skill whenever a .pptx or .potx file is involved — creating slide decks or presentations, reading or extracting their content, editing or updating existing decks, duplicating or reordering slides, filling templates (.potx), or working with layouts, speaker notes, or comments. Trigger on any mention of 'deck', 'slides', 'presentation', a .pptx/.potx filename, or any task that requires opening, producing, or modifying a PowerPoint file."
---

# PPTX: create, edit, analyze

A `.pptx` is a ZIP archive of XML parts. Pick the approach by task:

| Task | Approach |
|---|---|
| **Create** a new deck | write a `pptxgenjs` script (see its gotchas below) |
| **Edit / duplicate / reorder** slides, or fill a template | unpack → edit XML → repack; use `scripts/add_slide.py` and `scripts/clean.py` for the package bookkeeping |
| **Read** content | `markitdown deck.pptx` (one `<!-- Slide number: N -->` block per slide) |

## Scripts

All paths relative to this skill's directory.

| Script | What it does |
|---|---|
| `scripts/add_slide.py` | Duplicate a slide or instantiate a layout with all package bookkeeping (content types, rels, `<p:sldIdLst>`). Works on an unpacked dir or a packed file (`--output` / `--in-place`) |
| `scripts/clean.py` | Delete slides no longer listed in `<p:sldIdLst>` plus every part nothing references anymore. Run **after** the slide list is final |
| `scripts/office/validate.py` | XSD-validate every XML part against ECMA-376 schemas; check rels resolve and `[Content_Types].xml` covers every part. `--original SRC` baselines errors a template already has |
| `scripts/thumbnail.py` | Labeled grid of every slide (labels = XML part names) for picking template layouts. `.pptx` only |

Dependencies: Python `defusedxml`, `lxml`, `Pillow`, `pymupdf`; LibreOffice
(`soffice`) or — on Windows with Office — `pywin32` for rendering;
`pdftoppm` (Poppler) optional (PyMuPDF substitutes). `markitdown[pptx]` for text dumps.

## Editing an existing deck — the working loop

```bash
mkdir unpacked && cd unpacked && unzip -X ../deck.pptx    # -X: no extra attrs
# ... make structural changes first (below), then content edits ...
python scripts/clean.py unpacked/          # drop orphaned parts after slide list is final
(cd unpacked && rm -f ../out.pptx && zip -Xr ../out.pptx .)   # pack from INSIDE the dir
python scripts/office/validate.py out.pptx --original deck.pptx
```

**Do all structural work — add, delete, reorder — before editing any
slide's content.** `add_slide.py` copies the source slide verbatim, so
duplicating after editing clones your edits; `clean.py` deletes any
slide missing from `<p:sldIdLst>`, including one you just wrote.

Rules that save the deck:

- **Never copy a slide file by hand.** A new slide needs an entry in
  `[Content_Types].xml`, a relationship in `ppt/_rels/presentation.xml.rels`,
  an `<p:sldId>` with a fresh unique id, and a `.rels` of its own —
  `add_slide.py` does all of it. On a packed file pass `--output`, or it
  rewrites the input.
- A duplicated slide still *references* the source's chart/SmartArt parts
  rather than cloning them: editing one edits the other. Clone the part
  and repoint the relationship if you need an independent copy.
- `python-pptx` pitfalls, if you script with it instead: it cannot
  duplicate a slide (`add_slide(layout)` is its only entry point),
  `text_frame.text = "..."` collapses a paragraph to one unstyled run —
  assign `run.text` — and `add_picture` raises on the SVG/EMF many
  templates embed.
- Round-trip OOXML through `defusedxml.minidom`, never
  `xml.etree.ElementTree` — ElementTree rewrites namespace prefixes and
  corrupts the file.
- Legacy `.ppt` must be converted first. `.potx` unpacks and packs the
  same way — keep the `.potx` extension on output.
- Template slots ≠ your items: with 4 placeholder team members and 3 real
  ones, delete the 4th member's entire group (image + text boxes), not
  just its text.
- One `<a:p>` per list item; copy the sibling `<a:pPr>` to keep spacing;
  `b="1"` on the `<a:rPr>` of labels like `Status:`. Bullets inherit from
  the layout — `<a:buChar>`/`<a:buAutoNum>`/`<a:buNone>` only to override,
  never a literal `•`. Text with leading/trailing spaces needs
  `xml:space="preserve"` on its `<a:t>`.

## Creating with pptxgenjs — footguns

`pptxgenjs` comes preinstalled with Node; only `npm install pptxgenjs` if
the `require` fails. The API reference is elsewhere — these are the
failure modes:

- **Set `pres.layout` before adding slides.** The default canvas is
  `LAYOUT_16x9` = 10" × 5.625", not 13.3" wide. Shapes past the edge are
  written, not clamped — they land off-slide. (`LAYOUT_WIDE` is 13.3" × 7.5".)
- **Hex colors: no `#`, no 8-digit RGBA** — `color: "FF0000"`. Both
  `"#FF0000"` and `"00000020"` corrupt the file. Translucency is
  `transparency: 0-100` on fills/images, `opacity: 0-1` on shadows —
  each is silently ignored on the other.
- **pptxgenjs mutates option objects in place** (values become EMU on
  first use). Build a fresh `shadow`/options object per `add*` call.
- **Shadow `offset` must be ≥ 0** — negative offsets corrupt the file.
  Shadow upward with `angle: 270` and a positive offset.
- **`letterSpacing` is silently ignored** — the real option is `charSpacing`.

## Typography

**Font names are resolved by the viewer's PowerPoint, not by your
environment.** Any visual QA you render uses substituted fonts, and some
substitutes have different widths — so preview overflow can lie both ways.

- Safe fonts (metric-true in QA and shipped with Office): **Arial,
  Calibri, Cambria, Times New Roman, Courier New, Bookman Old Style,
  Century Schoolbook**. Use them for body text and anywhere fit matters.
- Personality at zero risk: safe serif header (Cambria, Bookman Old
  Style, Century Schoolbook) + safe sans body (Calibri, Arial).
- Asked for an off-list font (Georgia, Trebuchet MS...)? Use it where
  asked, size those containers with ~10% slack, and don't trust QA
  text-fit on those elements.
- QA-unreliable (substitute has different widths): Georgia, Trebuchet MS,
  Impact, Arial Black, Garamond, Consolas, Palatino Linospace; Calibri
  Light varies by environment. Fine for titles with slack.
- Never default to Aptos — no metric-compatible substitute here and
  missing from older Office installs.

## Slide design that doesn't read as AI filler

- **Pick a palette for THIS topic** — if swapping your colors into a
  different deck still "works", the choice wasn't specific. One dominant
  color (60-70% of visual weight), 1-2 supporting tones, one sharp accent.
- Dark title + conclusion slides around light content ("sandwich"), or
  dark throughout for a premium feel. Avoid cream/beige defaults
  (`F5F5DC`, `FAF0E6`, `FAEBD7`, `FFF8E1`) — white or the brand palette.
- Commit to ONE visual motif (rounded image frames, icons in colored
  circles) and repeat it across slides.
- **Every slide needs a visual element** — image, chart, icon, shape.
  Text-only slides are forgettable. Layout options: two-column, icon +
  text rows, 2x2/2x3 grid, half-bleed image with overlay. Data: large
  stat callouts (60-72pt numbers, small labels), comparison columns,
  timelines.
- Sizing: slide title 36-44pt bold; section header 20-24pt; body 14-16pt;
  captions 10-12pt muted. ≥0.5" margins, consistent 0.3-0.5" gaps,
  left-align body text (center only titles).
- **Never**: accent lines under titles, decorative color bars or
  edge stripes (header/footer bars, sidebar stripes, single-side card
  borders — all read as generated filler). Separate cards with a subtle
  background tint, drop shadow, or icon instead.
- Vary layouts across slides; don't style one slide and leave the rest
  plain; check contrast for text AND icons.

## QA — required before delivering

Your first render usually has real issues. Find, fix, re-render only the
changed slides, stop.

**Content QA** — `markitdown output.pptx`: missing content, typos, wrong
order. For template work: leftover placeholder text (`grep -iE "lorem|ipsum|\[insert|click to"` on the markitdown output).

**File QA**:

```bash
python scripts/office/validate.py output.pptx                       # from scratch
python scripts/office/validate.py output.pptx --original src.pptx   # from a template
```

Always pass `--original` for template-derived decks: templates often
contain parts the XSD itself rejects, and without the baseline a genuine
regression hides among template noise. Structural checks (rels, content
types) always run in full.

Known trap: pptxgenjs emits chart XML that PowerPoint refuses to open
while python-pptx, LibreOffice, and the XSD all accept it — the failure
names its fix; fix the generator and rebuild.

**Visual QA** — convert to images and actually look at every one, fresh
(a subagent is good for this — after writing the code you see what you
expect, not what rendered):

```bash
soffice --headless --convert-to pdf output.pptx   # or PowerPoint COM on Windows
pdftoppm -jpeg -r 150 output.pdf slide            # PyMuPDF substitutes if absent
```

Look for, in order: **text overflow/cut-off at a box or slide boundary**
(most common, always user-visible), overlapping elements, citations or
footers colliding with content, gaps < 0.3" or uneven, margins < 0.5",
misaligned columns, low-contrast text or icons, template decoration
mispositioned after text replacement, leftover placeholders.
