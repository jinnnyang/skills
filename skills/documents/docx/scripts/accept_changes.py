"""Produce a clean copy of a docx with tracked changes (redlining) accepted.

Word records edits with <w:ins> (inserted) and <w:del> (deleted) runs plus
<w:pPrChange> entries for paragraph-level changes. This script rewrites
word/document.xml so the edits are applied as final text:

  - <w:ins>   -> unwrapped; the inserted runs become normal runs
  - <w:del>   -> removed entirely (its <w:delText> content is dropped)
  - <w:pPrChange> for a deleted paragraph mark -> the following paragraph is
    joined into the previous one (the deleted break is gone)

Usage:
    python scripts/accept_changes.py doc.docx [--output OUT.docx]
    python scripts/accept_changes.py unpacked_dir/   # directory, in place
    --drop-empty   remove paragraphs left with no content after accepting

After accepting, run validate.py. A known leftover: a list item whose text
was fully deleted still renders its bullet once the text is gone; pass
--drop-empty to strip those (and any other now-blank paragraphs).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.dom.minidom import parseString

sys.path.insert(0, str(Path(__file__).resolve().parent))

from office.pkg import OOXML_FAMILY, rezip, safe_extract  # noqa: E402

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def child(parent, localname):
    for n in parent.childNodes:
        if n.nodeType == n.ELEMENT_NODE and n.localName == localname and n.namespaceURI == W:
            return n
    return None


def children(parent, localname):
    return [
        n for n in parent.childNodes
        if n.nodeType == n.ELEMENT_NODE and n.localName == localname and n.namespaceURI == W
    ]


def prev_paragraph(par):
    """Previous sibling <w:p> element, or None."""
    node = par.previousSibling
    while node is not None:
        if node.nodeType == node.ELEMENT_NODE and node.localName == "p" and node.namespaceURI == W:
            return node
        node = node.previousSibling
    return None


def apply_changes(doc, drop_empty: bool) -> tuple[int, int, int]:
    """Accept tracked changes. Returns (inserts, deletes, joins)."""
    n_ins = n_del = n_join = 0

    # 1. paragraph-mark deletion joins (pPrChange containing a w:del).
    #    Must run before <w:del> removal so the marker is still visible.
    for par in list(doc.getElementsByTagNameNS(W, "p")):
        ppr = child(par, "pPr")
        if ppr is None:
            continue
        change = child(ppr, "pPrChange")
        if change is None:
            continue
        ppr_new = child(change, "pPr")
        rpr = child(ppr_new, "rPr") if ppr_new is not None else None
        if rpr is not None and child(rpr, "del") is not None:
            # deleted paragraph mark: drop the change, join into previous
            ppr.removeChild(change)
            prev = prev_paragraph(par)
            if prev is not None:
                for node in list(par.childNodes):
                    prev.appendChild(node)
                par.parentNode.removeChild(par)
                n_join += 1

    # 2. unwrap <w:ins>
    for ins in list(doc.getElementsByTagNameNS(W, "ins")):
        parent = ins.parentNode
        while ins.firstChild:
            parent.insertBefore(ins.firstChild, ins)
        parent.removeChild(ins)
        n_ins += 1

    # 3. remove remaining <w:del> (text deletions)
    for dele in list(doc.getElementsByTagNameNS(W, "del")):
        dele.parentNode.removeChild(dele)
        n_del += 1

    # 4. optionally drop now-empty paragraphs (the empty-bullet artifact)
    if drop_empty:
        for par in list(doc.getElementsByTagNameNS(W, "p")):
            if paragraph_empty(par):
                # keep the body's trailing empty paragraph that hosts <w:sectPr>
                if child(par, "pPr") is None and not paragraph_has_content(par):
                    if has_sibling_paragraph_content(par):
                        par.parentNode.removeChild(par)

    return n_ins, n_del, n_join


def paragraph_has_content(par):
    for n in par.childNodes:
        if n.nodeType == n.ELEMENT_NODE and n.localName not in ("pPr",):
            return True
    return False


def paragraph_empty(par):
    return not paragraph_has_content(par)


def has_sibling_paragraph_content(par):
    """True if any sibling paragraph still holds content (so an empty
    trailing paragraph is not the only content carrier)."""
    parent = par.parentNode
    if parent is None:
        return False
    for n in parent.childNodes:
        if n.nodeType == n.ELEMENT_NODE and n is not par and n.localName in ("p", "tbl"):
            return True
    return False


def process(document_xml: str, drop_empty: bool) -> tuple[str, tuple[int, int, int]]:
    doc = parseString(document_xml)
    counts = apply_changes(doc, drop_empty)
    return doc.toxml(encoding="UTF-8"), counts


def main() -> int:
    ap = argparse.ArgumentParser(description="Accept tracked changes in a docx, producing clean copy.")
    ap.add_argument("target", help="unpacked directory or packed .docx/.dotx")
    ap.add_argument("--output", help="packed output path (requires a packed input)")
    ap.add_argument("--drop-empty", action="store_true", help="remove paragraphs left empty after accepting")
    args = ap.parse_args()

    target = Path(args.target)
    if target.is_dir():
        doc_path = target / "word" / "document.xml"
        if not doc_path.is_file():
            print(f"Error: no word/document.xml in {target}", file=sys.stderr)
            return 2
        new_xml, counts = process(doc_path.read_bytes(), args.drop_empty)
        doc_path.write_bytes(new_xml)
        _report(counts)
        return 0

    if target.suffix.lower() not in OOXML_FAMILY:
        print(f"Error: unsupported file type {target.suffix!r}", file=sys.stderr)
        return 2
    out = Path(args.output) if args.output else target
    tmp_ctx = tempfile.TemporaryDirectory()
    unpacked = Path(tmp_ctx.name) / "pkg"
    unpacked.mkdir(parents=True)
    with zipfile.ZipFile(target) as zf:
        safe_extract(zf, unpacked)
    doc_path = unpacked / "word" / "document.xml"
    if not doc_path.is_file():
        print(f"Error: no word/document.xml in {target}", file=sys.stderr)
        return 2
    new_xml, counts = process(doc_path.read_bytes(), args.drop_empty)
    doc_path.write_bytes(new_xml)
    rezip(unpacked, out)
    tmp_ctx.cleanup()
    _report(counts)
    return 0


def _report(counts):
    n_ins, n_del, n_join = counts
    print(f"Accepted {n_ins} insertion(s), {n_del} deletion(s), {n_join} paragraph join(s).")


if __name__ == "__main__":
    sys.exit(main())
