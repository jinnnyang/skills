"""Add a slide to a PPTX: duplicate an existing slide or instantiate a layout.

Performs all package bookkeeping a new slide needs, so the deck stays
valid after the operation:

  - writes ppt/slides/slideN.xml (verbatim copy of the source slide, or a
    minimal empty slide when instantiating a layout)
  - writes the slide's .rels pointing at the source's layout, dropping the
    source's notesSlide reference (speaker notes are per-slide and must
    not be shared)
  - registers the part in [Content_Types].xml
  - adds a slide relationship with a fresh rId to ppt/_rels/presentation.xml.rels
  - inserts <p:sldId id="..." r:id="..."/> into <p:sldIdLst> — at the end,
    or right after --after SLIDE

Works on an unpacked directory or directly on a .pptx/.potx file (use
--output, or --in-place to rewrite the input).

A duplicated slide keeps the source's XML content verbatim — edit the new
slide file afterwards to change it. The duplicate still *references* the
source's chart/SmartArt/embedded-object parts instead of cloning them:
editing one slide's chart edits the other's.

Usage:
    python add_slide.py unpacked/ slide2.xml
    python add_slide.py unpacked/ slide2.xml --after slide2.xml
    python add_slide.py unpacked/ slideLayout3.xml
    python add_slide.py deck.pptx slide2.xml --output out.pptx
    python add_slide.py deck.pptx slide2.xml --in-place
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from office.pkg import (  # noqa: E402
    NS_P,
    NS_R,
    OOXML_FAMILY,
    RelsFile,
    SLIDE_CONTENT_TYPE,
    SLIDE_LAYOUT_CONTENT_TYPE,
    SLIDE_LAYOUT_REL_TYPE,
    SLIDE_REL_TYPE,
    content_types_add_override,
    next_free_name,
    parse_part,
    parse_xml,
    part_text,
    rel_target,
    rels_path_for,
    rezip,
    safe_extract,
    slide_number,
    target_part_path,
)

MINIMAL_SLIDE_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr/>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr>
    <a:masterClrMapping/>
  </p:clrMapOvr>
</p:sld>
"""


def fail(msg: str):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(2)


def classify_source(name: str) -> tuple[str, str]:
    """(content type, relationship type) for the part being added."""
    if re.fullmatch(r"slide\d+\.xml", name):
        return SLIDE_CONTENT_TYPE, SLIDE_REL_TYPE
    if re.fullmatch(r"slideLayout\d+\.xml", name):
        return SLIDE_LAYOUT_CONTENT_TYPE, SLIDE_LAYOUT_REL_TYPE
    fail(f"unsupported source part: {name} (want slideN.xml or slideLayoutN.xml)")
    raise AssertionError("unreachable")  # fail() exits


def find_source(unpacked: Path, name: str) -> Path:
    """Locate slideN.xml or slideLayoutN.xml under the unpacked root."""
    direct = unpacked / name
    if direct.is_file():
        return direct
    hits = sorted(unpacked.rglob(name))
    if not hits:
        fail(f"{name} not found in package")
    if len(hits) > 1:
        fail(f"{name} is ambiguous: {[str(h.relative_to(unpacked).as_posix()) for h in hits]}")
    return hits[0]


def layout_of(unpacked: Path, slide_part: str) -> str | None:
    """Package-relative layout path a slide points at, if any."""
    rels = RelsFile(unpacked / rels_path_for(slide_part))
    hits = rels.find_by_type(SLIDE_LAYOUT_REL_TYPE)
    if not hits:
        return None
    return target_part_path(slide_part, hits[0]["Target"])


def slide_ids_in_order(unpacked: Path) -> list[tuple[str, str]]:
    """(rId, package part path) for each <p:sldId> in presentation order."""
    pres = unpacked / "ppt" / "presentation.xml"
    rels = RelsFile(unpacked / "ppt" / "_rels" / "presentation.xml.rels")
    out = []
    for e in parse_part(pres).getElementsByTagName("p:sldId"):
        rid = e.getAttribute("r:id") or e.getAttributeNS(NS_R, "id")
        target = rels.target_of(rid)
        if target:
            out.append((rid, target_part_path("ppt/presentation.xml", target)))
    return out


def add_slide(unpacked: Path, source_name: str, after: str | None) -> Path:
    src = find_source(unpacked, source_name)
    src_part = src.relative_to(unpacked).as_posix()
    ctype, rel_type = classify_source(src.name)

    slides_dir = unpacked / "ppt" / "slides"
    if not slides_dir.is_dir():
        fail("package has no ppt/slides/ — is this a presentation?")
    new_name = next_free_name(slides_dir, "slide%d.xml")
    new_part = f"ppt/slides/{new_name}"
    new_path = unpacked / new_part

    if re.fullmatch(r"slideLayout\d+\.xml", src.name):
        new_path.write_text(MINIMAL_SLIDE_XML, encoding="utf-8")
        layout_part = src_part
    else:
        shutil.copyfile(src, new_path)
        layout_part = layout_of(unpacked, src_part) or ""
        if not layout_part:
            fail(f"{src_part} has no slideLayout relationship to copy")

    # slide .rels: just the layout. Nothing else carries over from the
    # source — a notesSlide reference especially (notes are per-slide).
    rels = RelsFile(unpacked / rels_path_for(new_part))
    rels.entries = [
        {"Id": "rId1", "Type": SLIDE_LAYOUT_REL_TYPE, "Target": rel_target(new_part, layout_part)}
    ]
    rels.save()

    content_types_add_override(unpacked, new_part, ctype)

    pres_rels = RelsFile(unpacked / "ppt" / "_rels" / "presentation.xml.rels")
    rid = pres_rels.add(SLIDE_REL_TYPE, rel_target("ppt/presentation.xml", new_part))
    pres_rels.save()

    _insert_sld_id(unpacked, rid, after)
    print(f"Created {new_part} from {src_part}")
    return new_path


def _insert_sld_id(unpacked: Path, rid: str, after: str | None) -> None:
    pres_path = unpacked / "ppt" / "presentation.xml"
    if not pres_path.is_file():
        fail("ppt/presentation.xml missing")
    doc = parse_part(pres_path)
    lists = doc.getElementsByTagName("p:sldIdLst")
    if not lists:
        fail("<p:sldIdLst> not found in presentation.xml")
    sld_lst = lists[0]

    used = set()
    for e in sld_lst.getElementsByTagName("p:sldId"):
        if e.getAttribute("id").isdigit():
            used.add(int(e.getAttribute("id")))
    new_id = max(used | {255}) + 1

    el = doc.createElement("p:sldId")
    el.setAttribute("id", str(new_id))
    el.setAttributeNS(NS_R, "r:id", rid)

    anchor = None
    if after:
        want = slide_number(after)
        if not want:
            fail(f"--after {after} is not a slideN.xml name")
        order = slide_ids_in_order(unpacked)
        for i, (_, part) in enumerate(order):
            if slide_number(Path(part).name) == want:
                # position i in sldIdLst corresponds to the i-th p:sldId child
                ids = sld_lst.getElementsByTagName("p:sldId")
                anchor = ids[i]
                break
        if anchor is None:
            fail(f"--after {after}: slide not present in <p:sldIdLst>")
        parent = anchor.parentNode
        assert parent is not None
        parent.insertBefore(el, anchor.nextSibling)
    else:
        sld_lst.appendChild(el)

    pres_path.write_bytes(doc.toxml(encoding="UTF-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Add (duplicate or instantiate) a slide in a PPTX.")
    ap.add_argument("package", help="unpacked directory or .pptx/.potx file")
    ap.add_argument("source", help="slideN.xml to duplicate, or slideLayoutN.xml")
    ap.add_argument("--after", help="insert right after this slideN.xml (default: at the end)")
    ap.add_argument("--output", "-o", help="output path when PACKAGE is a packed file")
    ap.add_argument("--in-place", action="store_true", help="rewrite the packed input file")
    args = ap.parse_args()

    pkg_path = Path(args.package)
    if not pkg_path.exists():
        fail(f"{pkg_path} does not exist")

    if pkg_path.is_dir():
        add_slide(pkg_path, args.source, args.after)
        return 0

    if pkg_path.suffix.lower() not in OOXML_FAMILY:
        fail(f"{pkg_path} is not a .pptx/.potx file or a directory")
    if args.output and args.in_place:
        fail("--output and --in-place are mutually exclusive")
    out = Path(args.output) if args.output else (pkg_path if args.in_place else None)
    if out is None:
        fail("pass --output OUT.pptx or --in-place when PACKAGE is a packed file")

    with tempfile.TemporaryDirectory(prefix="add_slide_") as td:
        unpacked = Path(td) / "pkg"
        with zipfile.ZipFile(pkg_path) as zf:
            safe_extract(zf, unpacked)
        new_part = add_slide(unpacked, args.source, args.after)
        rezip(unpacked, out)
    print(f"Wrote {out} ({new_part.name} added)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
