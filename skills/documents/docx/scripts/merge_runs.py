"""Merge adjacent runs with identical formatting in word/document.xml.

Word frequently splits one visible phrase across many <w:r> elements (one
run per formatting change, per style edit, or just per paste). That makes
find-and-replace miss the text because the string you search for is never
contiguous in the XML. This script folds runs that carry the same run
properties (same <w:rPr>, or neither) back into a single run so the text
reads contiguously again.

Usage:
    python scripts/merge_runs.py document.docx [--output OUT.docx]   # packed
    python scripts/merge_runs.py unpacked_dir/                       # directory, in place

Runs are only merged when their formatting is byte-identical. A run that
splits a word at a formatting boundary is left alone; only genuinely
redundant adjacent runs collapse.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.dom.minidom import parseString

sys.path.insert(0, str(Path(__file__).resolve().parent))

from office.pkg import OOXML_FAMILY, rezip, safe_extract  # noqa: E402

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def local(name: str) -> bool:
    return name.startswith("w:") or name.startswith("{" + W + "}")


def child_elements(parent, localname: str) -> list:
    return [n for n in parent.childNodes if n.nodeType == n.ELEMENT_NODE and local(n.nodeName) and n.localName == localname]


def run_signature(run) -> str:
    """Serialized <w:rPr> of a run ('' when it has none)."""
    rprs = child_elements(run, "rPr")
    return rprs[0].toxml() if rprs else ""


def merge_paragraph(par) -> int:
    """Fold adjacent same-formatting runs; return number of runs removed."""
    runs = child_elements(par, "r")
    merged = 0
    i = 0
    while i < len(runs) - 1:
        cur = runs[i]
        sig = run_signature(cur)
        j = i + 1
        while j < len(runs) and run_signature(runs[j]) == sig:
            nxt = runs[j]
            # append next run's text runs into the current run
            for t in child_elements(nxt, "t"):
                t_el = None
                existing = child_elements(cur, "t")
                # pick the last text element in cur to append into
                target = existing[-1] if existing else None
                if target is None:
                    # cur has no text; adopt nxt's <w:t> wholesale
                    cur.appendChild(t.cloneNode(True))
                else:
                    # append nxt's text content, keep xml:space if any side preserves
                    text = first_text(t)
                    if t.getAttribute("xml:space") == "preserve" or target.getAttribute("xml:space") == "preserve":
                        target.setAttribute("xml:space", "preserve")
                    target.appendChild(doc_text(target, text))
            cur.parentNode.removeChild(nxt)
            merged += 1
            j += 1
        runs = child_elements(par, "r")
        i += 1
    return merged


def first_text(el):
    parts = []
    for n in el.childNodes:
        if n.nodeType == n.TEXT_NODE:
            parts.append(n.data)
    return "".join(parts)


def doc_text(parent, data: str):
    import xml.dom.minidom
    return parent.ownerDocument.createTextNode(data)


def process(document_xml: str) -> tuple[str, int]:
    doc = parseString(document_xml)
    total = 0
    for par in doc.getElementsByTagNameNS(W, "p"):
        total += merge_paragraph(par)
    return doc.toxml(encoding="UTF-8"), total


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge adjacent identically-formatted runs in a docx.")
    ap.add_argument("target", help="unpacked directory or packed .docx/.dotx")
    ap.add_argument("--output", help="packed output path (requires a packed input)")
    args = ap.parse_args()

    target = Path(args.target)
    if target.is_dir():
        doc_path = target / "word" / "document.xml"
        if not doc_path.is_file():
            print(f"Error: no word/document.xml in {target}", file=sys.stderr)
            return 2
        new_xml, merged = process(doc_path.read_bytes())
        doc_path.write_bytes(new_xml)
        print(f"Merged {merged} run(s) in {target}/word/document.xml")
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
    new_xml, merged = process(doc_path.read_bytes())
    doc_path.write_bytes(new_xml)
    rezip(unpacked, out)
    tmp_ctx.cleanup()
    print(f"Merged {merged} run(s) in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
